// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 ZeroDDS Contributors
//! `shape_main` — ZeroDDS reference client for the OMG `dds-rtps`
//! interoperability test suite (`github.com/omg-dds/dds-rtps`).
//!
//! BUILD + LOCAL-VALIDATE phase artifact. This binary is **not**
//! submitted anywhere — no CLA PR, no source PR, no release asset, no
//! push to `github.com/omg-dds`. That step is held back for Sandra.
//!
//! It is a thin CLI + protocol shim over ZeroDDS's existing DCPS API
//! (`crates/dcps`) and QoS machinery (`crates/qos`) — no new wire/CDR/QoS
//! code lives here. See `tools/omg-shape-main/README.md` for the full
//! flag-coverage table and the exact `pexpect` strings this binary
//! reproduces.

#![allow(clippy::print_stdout, clippy::print_stderr)]

mod cli;
mod listeners;
mod qos_map;
mod shape_filter;
mod shape_type;

use std::cell::Cell;
use std::io::Write;
use std::process::ExitCode;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration as StdDuration;

use clap::Parser;

use crate::shape_type::ShapeType;
use zerodds_dcps::psm_constants::status as status_bits;
use zerodds_dcps::runtime::RuntimeConfig;
use zerodds_dcps::{
    DataReader, DataWriter, DdsType, DomainParticipant, DomainParticipantFactory,
    DomainParticipantQos, HANDLE_NIL, InstanceHandle, InstanceStateKind, Sample, TopicQos,
};

use zerodds_rtps::dialect::{EndOfSetForm, GroupWireForm, WriterGroupInfoWidth};
use zerodds_rtps::wire_types::VendorId;

use cli::{AccessScopeArg, FinalInstanceStateArg, Options};
use listeners::ShapeListener;

type BoxError = Box<dyn std::error::Error>;

/// `-v d` diagnostic. Goes to **stderr**, never to stdout: the harness
/// `pexpect`-matches stdout, so the two verbosity levels must produce the
/// same stdout byte for byte.
macro_rules! debugln {
    ($opts:expr, $($arg:tt)*) => {
        if $opts.debug_verbosity() {
            eprintln!("shape_main: debug: {}", format_args!($($arg)*));
        }
    };
}

fn main() -> ExitCode {
    let opts = Options::parse();
    if opts.publish == opts.subscribe {
        eprintln!("shape_main: exactly one of -P or -S is required");
        return ExitCode::FAILURE;
    }

    let stop = Arc::new(AtomicBool::new(false));
    {
        let stop = Arc::clone(&stop);
        if let Err(e) = ctrlc::set_handler(move || {
            stop.store(true, Ordering::SeqCst);
        }) {
            eprintln!("shape_main: warning: SIGINT handler not installed: {e}");
        }
    }

    let result = if opts.publish {
        run_publisher(&opts, &stop)
    } else {
        run_subscriber(&opts, &stop)
    };

    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("shape_main: error: {e}");
            ExitCode::FAILURE
        }
    }
}

/// `<base>`, `<base>1`, `<base>2`, ... — the `--num-instances` /
/// `--num-topics` naming convention documented in the README.
fn numbered(base: &str, n: u32) -> Vec<String> {
    (0..n.max(1))
        .map(|i| {
            if i == 0 {
                base.to_string()
            } else {
                format!("{base}{i}")
            }
        })
        .collect()
}

/// Canonical ShapesDemo sine-wave motion on the 240×270 canvas.
fn motion(t: f32) -> (i32, i32) {
    #[allow(clippy::cast_possible_truncation)]
    let x = (120.0 + 80.0 * t.sin()) as i32;
    #[allow(clippy::cast_possible_truncation)]
    let y = (135.0 + 90.0 * (t * 1.3).cos()) as i32;
    (x, y)
}

fn create_participant(
    factory: &DomainParticipantFactory,
    opts: &Options,
) -> zerodds_dcps::Result<DomainParticipant> {
    // Over the same layers `create_participant` reads (files, the
    // environment), not over the bare defaults: what this client sets adds
    // to the configuration and must not drop it.
    let mut config = RuntimeConfig::from_standard_paths().map_err(|error| {
        zerodds_dcps::DdsError::Configuration {
            message: error.to_string(),
        }
    })?;
    // The suite configures a Connext reader to answer a HEARTBEAT at once
    // and a Connext writer to answer a NACK at once
    // (srcCxx/shape_configurator_rti_connext_dds.h: `config_dr_qos`
    // `max_heartbeat_response_delay` 0, `config_dw_qos`
    // `max_nack_response_delay` 0); the readers and writers of this client
    // answer the same way. With the runtime's defaults, the 500 ms and
    // 200 ms of DDSI-RTPS 2.5 sections 8.4.10.1 and 8.4.7.1:
    // - a writer that sends no further ahead than its KEEP_LAST history
    //   holds overwrote samples before they were acknowledged: dust_dds
    //   0.15.0 -> ZeroDDS Test_History_0/1 red, green with 0 and 50 ms;
    // - a repair reached a Connext 7.7.0 reader 200 ms late, which kept the
    //   repaired sample alive that much longer: ZeroDDS -> Connext
    //   Test_Lifespan_0/1 read 4 consecutive samples, green with 0.
    // The Connext reader keeps its default `heartbeat_suppression_duration`
    // of 62.5 ms (include/ndds/dds_c/dds_c_infrastructure.h,
    // `DDS_RTPS_RELIABLE_READER_PROTOCOL_DEFAULT`), the readers of this
    // client as well: a reader that answers every HEARTBEAT at once asked
    // dust_dds 0.16.1, which puts one between the fragments of a sample,
    // again and again for every sample in flight (Test_LargeData_0: 1.5 GB
    // on the wire for 180 samples, a Cyclone reader 26 MB for 199; red when
    // the repair stalled at 457 of 500 samples).
    config.reader_heartbeat_response_delay = StdDuration::ZERO;
    config.reader_heartbeat_suppression_duration = StdDuration::from_micros(62_500);
    config.nack_response_delay = StdDuration::ZERO;
    suite_settings(&mut config, |name| std::env::var_os(name).is_some());
    if opts.periodic_announcement_ms > 0 {
        config.spdp_period = StdDuration::from_millis(u64::from(opts.periodic_announcement_ms));
    }
    let participant = factory.create_participant_with_config(
        opts.domain_id,
        DomainParticipantQos::default(),
        config,
    )?;
    vendor_forms(
        &participant,
        std::env::var_os("ZERODDS_WRITER_GROUP_INFO_ON_WIRE").is_none(),
    );
    Ok(participant)
}

/// The forms the participants of some vendors get, picked by the vendorId
/// each announces; every other peer gets the specification's.
///
/// Connext 7.7.0, HDDS 1.4.8 and zzdds 0.3.2 read the sets of a GROUP-scope
/// publisher only in the form HDDS and zzdds send: each writer's coherent
/// set as at TOPIC scope, without the group information of DDSI-RTPS 2.5
/// sections 8.7.5 and 8.7.6 (`zerodds_rtps::dialect::GroupWireForm`).
/// Measured with that information: ZeroDDS -> Connext
/// Test_CoherentSets_18/_21, -> HDDS and -> zzdds Test_CoherentSets_12/_21
/// red; without it green. `group_form` is false when the environment names
/// `ZERODDS_WRITER_GROUP_INFO_ON_WIRE`.
///
/// InterCOM 4.3.1 takes the end of a writer's coherent set as a GAP, not as
/// the DATA of Table 9.22 (`zerodds_rtps::dialect::EndOfSetForm`; measured:
/// ZeroDDS -> InterCOM Test_CoherentSets_10/_19 DATA_NOT_RECEIVED, the
/// reader requesting the end DATA again and again).
///
/// Dust 0.17.0 reads `PID_WRITER_GROUP_INFO` as sixteen octets and drops a
/// DATA that carries the four of DDSI-RTPS 2.5 §9.3.2.5
/// (`zerodds_rtps::dialect::WriterGroupInfoWidth`; measured: ZeroDDS -> Dust
/// the 14 GROUP-scope cases of CoherentSets and OrderedAccess
/// DATA_NOT_RECEIVED, green without the parameter).
fn vendor_forms(participant: &DomainParticipant, group_form: bool) {
    let Some(runtime) = participant.runtime() else {
        return;
    };
    if group_form {
        let form = runtime
            .user_writer_behaviour()
            .with_group_wire_form(GroupWireForm::CoherentSetsOnly);
        for vendor in [VendorId::RTI_CONNEXT, VendorId::HDDS, VendorId::ZZDDS] {
            runtime.set_vendor_rtps_behaviour(vendor, form);
        }
    }
    runtime.set_vendor_rtps_behaviour(
        VendorId::INTERCOM,
        runtime
            .user_writer_behaviour()
            .with_end_of_set_form(EndOfSetForm::Gap),
    );
    runtime.set_vendor_rtps_behaviour(
        VendorId::DUST,
        runtime
            .user_writer_behaviour()
            .with_writer_group_info_width(WriterGroupInfoWidth::Sixteen),
    );
}

/// The settings the OMG dds-rtps suite needs of a ZeroDDS process that meets
/// the other vendors' `shape_main`, each unless the environment names it
/// (`named`). The runtime's defaults stay the readings of the specifications;
/// this client sets them so that a run without `run_vendors.sh` (the official
/// matrix starts the binary without an environment) gets them as well.
fn suite_settings(config: &mut RuntimeConfig, named: impl Fn(&str) -> bool) {
    // Fast DDS (and, as recorded, OpenDDS and RTI Connext) send the ACKNACK
    // of a reader that holds nothing with bitmapBase 0 and numBits 0, which
    // DDSI-RTPS 2.5 section 8.3.5.5 makes invalid; by default the rest of
    // such a datagram is dropped (section 8.3.4.1 rule 6), and with it the
    // SEDP data that follows in it (sec-diag16/17: every red
    // zerodds->fastdds cell had rejections, every green one none).
    if !named("ZERODDS_WIRE_ACCEPT_EMPTY_ACKNACK_BASE_ZERO") {
        config.accept_empty_acknack_base_zero = true;
    }
    // Cyclone DDS and RTI Connext write the length of a PL_CDR1 parameter
    // rounded up to four (DDSI-RTPS 2.5 section 9.4.2.11); XTypes 1.3
    // section 7.4.1.2.2 has the exact length, which the default reader
    // holds a parameter to.
    if !named("ZERODDS_WIRE_PL_CDR1_READING") {
        config.pl_cdr1_reading = zerodds_ast_layout::PlCdr1Reading::Tolerant;
    }
    // Test_FinalInstanceState_2 expects NOT_ALIVE_NO_WRITERS at the reader
    // when the publisher ends without unregistering or disposing; Connext
    // 7.7.0, Fast DDS 3.6.1, CoreDX 6.15.3 and HDDS 1.4.6 as the publisher
    // end there. A deleted DataWriter unregisters and, with
    // autodispose_unregistered_instances, disposes its instances by default
    // (DDS 1.4 sections 2.2.2.4.1.6 and 2.2.3.21); dds-rtps issue #92 names
    // the contradiction.
    if !named("ZERODDS_WRITER_UNREGISTER_ON_DELETE") {
        config.writer_unregister_on_delete = false;
    }
    // Fast DDS 3.6.1 announces PID_TYPE_MAX_SIZE_SERIALIZED 160 for ShapeType
    // and sends samples of 100 036 octets (Test_LargeData_0); the default
    // reader holds a payload to the dataMaxSizeSerialized of DDSI-RTPS 2.5
    // section 8.4.10.4 and read none of them.
    if !named("ZERODDS_READER_HONOR_DATA_MAX_SIZE_SERIALIZED") {
        config.reader_honor_data_max_size_serialized = false;
    }
    // OpenDDS 3.35.0-dev and InterCOM 4.3.1 dispose and unregister each
    // instance in one marker when their writer is deleted; the default reader
    // takes it as both (DDSI-RTPS 2.5 section 9.6.3.9) and ends at
    // NOT_ALIVE_DISPOSED where Test_FinalInstanceState_2 expects
    // NOT_ALIVE_NO_WRITERS (measured: 20 of 20 and 5 of 5 runs).
    if !named("ZERODDS_READER_DISPOSE_WITH_UNREGISTER") {
        config.reader_dispose_with_unregister = false;
    }
    // dust_dds 0.16.1 announces the key `color` of ShapeType as an unbounded
    // string: its `dust_dds_gen` compiles the suite's `string<128>` to a
    // TypeObject with bound 0. The default reader refuses such a writer under
    // XTypes 1.3 Table 19, a key member of the reader shorter than the
    // writer's (measured: dust_dds -> ZeroDDS 50 cases DATA_NOT_RECEIVED,
    // event `type.inconsistent`); Connext, Cyclone, Fast DDS, OpenDDS, CoreDX,
    // InterCOM and zzdds receive from it in Test_Domain_0 of the published run.
    if !named("ZERODDS_KEY_MEMBER_BOUNDS") {
        config.key_member_bounds = zerodds_types::assignability::KeyMemberBounds::Ignored;
    }
}

// ============================================================================
// Publisher
// ============================================================================

struct WriterCtx {
    topic_name: String,
    writer: DataWriter<ShapeType>,
    instances: Vec<(String, InstanceHandle)>,
}

fn run_publisher(opts: &Options, stop: &Arc<AtomicBool>) -> Result<(), BoxError> {
    let factory = DomainParticipantFactory::instance();
    let participant = create_participant(factory, opts)?;
    let publisher = participant.create_publisher(qos_map::publisher_qos(opts));

    let topic_names = numbered(&opts.topic_name, opts.num_topics);
    let colors = numbered(opts.resolved_color(), opts.num_instances);
    let base_size = if opts.shapesize <= 0 {
        20
    } else {
        opts.shapesize
    };

    let mut writers = Vec::with_capacity(topic_names.len());
    for tname in &topic_names {
        println!("Create topic: {tname}");
        let topic = participant.create_topic::<ShapeType>(tname, TopicQos::default())?;
        let writer = publisher.create_datawriter::<ShapeType>(&topic, qos_map::writer_qos(opts))?;
        println!(
            "Create writer for topic: {tname} color: {}",
            opts.resolved_color()
        );
        let listener = Arc::new(ShapeListener::new(tname.clone(), ShapeType::TYPE_NAME));
        writer.set_listener(Some(listener), status_bits::ANY);

        let mut instances = Vec::with_capacity(colors.len());
        for color in &colors {
            let seed = ShapeType::new(color.clone(), 0, 0, base_size);
            let handle = writer.register_instance(&seed)?;
            instances.push((color.clone(), handle));
        }
        writers.push(WriterCtx {
            topic_name: tname.clone(),
            writer,
            instances,
        });
    }

    let write_period = StdDuration::from_millis(opts.write_period_ms.max(1));
    let mut iteration: u64 = 0;
    let mut t: f32 = 0.0;
    // `--coherent` (`-T`) + `--coherent-sample-count <n>` (`-H`): DDS 1.4
    // §2.2.2.4.1.8/.9. Each iteration writes exactly one sample per
    // writer+instance, so a set of `n` samples per DataWriter+instance spans
    // `n` iterations. `begin_coherent_changes` opens the transaction on every
    // writer of the publisher; `end_coherent_changes` closes it and sends the
    // end-of-coherent-set marker (DDSI-RTPS 2.5 §8.7.6) that releases the set
    // on the subscriber.
    let coherent_set_size = u64::from(opts.coherent_set_size());
    let mut coherent_open = false;
    debugln!(
        opts,
        "publisher: topics={} instances={} coherent={} set_size={} payload={}",
        topic_names.len(),
        colors.len(),
        opts.coherent,
        coherent_set_size,
        opts.additional_payload_size
    );

    let additional_payload = payload_filler(opts.additional_payload_size as usize);

    let mut next_write = std::time::Instant::now() + write_period;
    // Under GROUP access scope a coherent or ordered publisher writes its
    // first sample once every writer has a matched reader, as the suite's
    // zzdds client does (srcZig/shape_main.zig, "coherent gating"). The
    // harness starts the publisher a second before the subscriber; a writer
    // that wrote before the match starts past SN 1 for the reader, and
    // Connext 7.7.0's GROUP subscriber then delivers none of its samples
    // (measured: ZeroDDS -> Connext Test_CoherentSets_8/_12 and
    // Test_OrderedAccess_8 red with the first DATA at SN 49 and 125; zzdds
    // and HDDS start at SN 1; CoreDX writes before the match and fails the
    // same three cases against Connext in the published run).
    let group_scope = matches!(opts.access_scope, Some(AccessScopeArg::G));
    let mut gated = (opts.coherent || opts.ordered) && group_scope;
    // A coherent publisher writes the iterations of one set without a pause
    // between them and paces after the set, so that no HEARTBEAT falls inside
    // an open set. A zzdds 0.3.2 reader takes a HEARTBEAT as the end of a
    // writer's set until it has seen that writer's end-of-coherent-set DATA
    // (src/dcps/reader.zig, `onHeartbeatCb`), and an InterCOM 4.3.1 reader
    // delivers next to nothing of sets with HEARTBEATs inside (measured:
    // ZeroDDS -> zzdds Test_CoherentSets_12 one sample per instance per read,
    // DATA_NOT_CORRECT; -> InterCOM Test_CoherentSets_10 36 sample lines
    // where HDDS, writing a set at once, reaches 5540). Order and sizes stay
    // those of the reference client; the rate stays one iteration per write
    // period.
    let burst_sets = opts.coherent;
    while !stop.load(Ordering::SeqCst) {
        if let Some(max) = opts.num_iterations
            && iteration >= max
        {
            break;
        }
        if gated {
            for wctx in &writers {
                wctx.writer.drive_listeners();
            }
            gated = !writers.iter().all(|wctx| {
                wctx.writer
                    .matched_subscriptions()
                    .is_ok_and(|readers| !readers.is_empty())
            });
            if gated {
                pace(&mut next_write, write_period);
                continue;
            }
        }
        if opts.coherent && iteration.is_multiple_of(coherent_set_size) {
            publisher.begin_coherent_changes()?;
            coherent_open = true;
            debugln!(opts, "begin_coherent_changes at iteration {iteration}");
        }
        let (x, y) = motion(t);
        // `-z 0`: "increase the size for every sample" — the harness treats
        // `[shapesize]` as an implicit per-instance sequence counter. Every
        // writer iteration writes one sample per instance with the *same*
        // `size`, and `size` increments by exactly 1 per iteration, so each
        // instance's successive samples are always +1 (RELIABLE checks require
        // exactly +1, BEST_EFFORT only strictly-increasing). The sequence
        // starts at 1 (`1, 2, 3, …`). `--size-modulo N` wraps it (`1..=N,
        // 1..=N, …`) for the official cases whose args pass `--size-modulo`;
        // without it the sequence stays unbounded (a wrap would otherwise
        // violate the strict-+1 RELIABLE checks). `-z N` (N != 0) = constant.
        #[allow(clippy::cast_possible_truncation, clippy::cast_possible_wrap)]
        let size = if opts.shapesize == 0 {
            let seq = iteration as i32;
            if opts.size_modulo > 0 {
                1 + (seq % opts.size_modulo as i32)
            } else {
                1 + seq
            }
        } else {
            opts.shapesize
        };
        for wctx in &writers {
            // Pump any pending writer-listener callbacks *before* writing, so a
            // match that already completed prints `on_publication_matched()`
            // ahead of this iteration's samples.
            wctx.writer.drive_listeners();
            for (color, _handle) in &wctx.instances {
                let sample =
                    ShapeType::with_payload(color.clone(), x, y, size, additional_payload.clone());
                wctx.writer.write(&sample)?;
                // Pump again after the write: the discovery/match that this
                // write drives must surface `on_publication_matched()` on stdout
                // *before* the sample line below. The official
                // `test_reliability_no_losses` check discards every publisher
                // sample up to and including the one at `on_publication_matched()`
                // and correlates from the next; the subscriber's first delivered
                // sample is the first one written after the match, so the match
                // line must precede that sample in stdout for the harness's
                // publisher queue and the subscriber's stream to align.
                wctx.writer.drive_listeners();
                if opts.print_writer_samples {
                    println!("{:<10} {color:<10} {x:03} {y:03} [{size}]", wctx.topic_name);
                    // Pipe stdout is block-buffered; flush each sample line so
                    // the pexpect-driven official harness reads it in real time
                    // rather than in bursts.
                    let _ = std::io::stdout().flush();
                }
            }
        }
        t += 0.15;
        iteration += 1;
        if coherent_open && iteration.is_multiple_of(coherent_set_size) {
            publisher.end_coherent_changes()?;
            coherent_open = false;
            debugln!(
                opts,
                "end_coherent_changes after iteration {}",
                iteration - 1
            );
        }
        if !burst_sets {
            pace(&mut next_write, write_period);
        } else if !coherent_open {
            pace(&mut next_write, write_period * opts.coherent_set_size());
        }
    }
    // A set left open by `--num-iterations` / SIGINT is closed here, so the
    // subscriber releases it instead of holding it forever (§2.2.2.4.1.9).
    if coherent_open {
        publisher.end_coherent_changes()?;
        debugln!(opts, "end_coherent_changes on loop exit");
    }

    if let Some(fis) = opts.final_instance_state {
        for wctx in &writers {
            for (color, handle) in &wctx.instances {
                let sample = ShapeType::new(color.clone(), 0, 0, base_size);
                match fis {
                    FinalInstanceStateArg::U => {
                        wctx.writer.unregister_instance(&sample, *handle)?;
                    }
                    FinalInstanceStateArg::D => {
                        wctx.writer.dispose(&sample, *handle)?;
                    }
                }
            }
        }
        // The readers are to see the unregister or dispose before they see
        // the writer go. The writer's end reaches them over SEDP, the markers
        // over the writer's own channel, so a reader could take the first and
        // drop the markers of a writer it no longer has (the instances then
        // end NOT_ALIVE_NO_WRITERS, Test_FinalInstanceState_1 with
        // `writer.unregister_on_delete=false`). The publisher waits for the
        // reliable readers to acknowledge the markers (DDS 1.4
        // §2.2.2.4.1.12) before it deletes the writer; a reader that does not
        // acknowledge in time does not keep it from finishing.
        for wctx in &writers {
            if let Err(e) = wctx.writer.wait_for_acknowledgments(FINAL_ACK_WAIT) {
                debugln!(
                    opts,
                    "wait_for_acknowledgments on {}: {e:?}",
                    wctx.topic_name
                );
            }
        }
    }
    Ok(())
}

/// How long the publisher waits for the acknowledgment of its final
/// unregister or dispose markers.
const FINAL_ACK_WAIT: StdDuration = StdDuration::from_secs(3);

// ============================================================================
// Subscriber
// ============================================================================

struct ReaderCtx {
    topic_name: String,
    reader: DataReader<ShapeType>,
    prev_instance: Cell<InstanceHandle>,
}

fn run_subscriber(opts: &Options, stop: &Arc<AtomicBool>) -> Result<(), BoxError> {
    let factory = DomainParticipantFactory::instance();
    let participant = create_participant(factory, opts)?;
    let subscriber = participant.create_subscriber(qos_map::subscriber_qos(opts));

    let topic_names = numbered(&opts.topic_name, opts.num_topics);
    let group_coherent = opts.coherent && matches!(opts.access_scope, Some(AccessScopeArg::G));

    let mut readers = Vec::with_capacity(topic_names.len());
    for tname in &topic_names {
        println!("Create topic: {tname}");
        let topic = participant.create_topic::<ShapeType>(tname, TopicQos::default())?;
        let mut reader =
            subscriber.create_datareader::<ShapeType>(&topic, qos_map::reader_qos(opts))?;

        if let Some(expr) = &opts.cft {
            match shape_filter::compile(expr) {
                Ok(f) => reader = reader.with_filter(f),
                Err(_) => {
                    println!("failed to create content filtered topic");
                    continue;
                }
            }
        } else if let Some(color) = opts.color.clone() {
            // README `-c <color>`: "color to publish (filter, if subscriber)".
            // On the subscribe side the flag is an instance filter — the
            // reader delivers only that color's instance. `--cft` wins when
            // both are given (it is the explicit expression).
            reader = reader.with_filter(move |s: &ShapeType| s.color == color);
        }

        println!("Create reader for topic: {tname} ");
        let listener = Arc::new(ShapeListener::new(tname.clone(), ShapeType::TYPE_NAME));
        reader.set_listener(Some(listener), status_bits::ANY);
        readers.push(ReaderCtx {
            topic_name: tname.clone(),
            reader,
            prev_instance: Cell::new(HANDLE_NIL),
        });
    }

    // README `--take-read`: uses take()/read() instead of
    // take_next_instance()/read_next_instance(). A `--cft` filter is only
    // documented to apply on the plain take()/read() path
    // (`DataReader::with_filter` doc comment), so a CFT forces this too.
    // `-c` on the subscribe side installs the same kind of filter.
    //
    // `--ordered` does NOT belong here: the reference application
    // (`srcCxx/shape_main.cxx`) cycles through the instances with
    // `take_next_instance` whatever PRESENTATION says, and the suite asks for
    // topic order only with `--take-read` (`Test_OrderedAccess_10`, `_17`).
    // `take_next_instance` returns one instance (DDS 1.4 §2.2.2.5.3.16).
    let use_plain = opts.take_read || opts.cft.is_some() || opts.color.is_some();

    let read_period = StdDuration::from_millis(opts.read_period_ms.max(1));
    let mut iteration: u64 = 0;
    // `Subscriber::begin_access`/`end_access` bracket the WHOLE topic loop,
    // not one reader — the access scope is the Subscriber's (§2.2.2.4.1.5),
    // and with GROUP scope the set spans its DataReaders. Mirrors
    // `srcCxx/shape_main.cxx`, which brackets on coherent OR ordered access,
    // and brackets under GROUP scope as well: DDS 1.4 §2.2.2.5.2.8 makes a
    // read or take there PRECONDITION_NOT_MET outside a bracket.
    let access_bracket = opts.coherent
        || opts.ordered
        || matches!(opts.access_scope, Some(crate::cli::AccessScopeArg::G));
    debugln!(
        opts,
        "subscriber: topics={} group_coherent={} ordered={} plain_read_path={}",
        readers.len(),
        group_coherent,
        opts.ordered,
        use_plain
    );

    let mut next_read = std::time::Instant::now() + read_period;
    while !stop.load(Ordering::SeqCst) {
        if let Some(max) = opts.num_iterations
            && iteration >= max
        {
            break;
        }
        // One marker per read iteration, ahead of the topic loop — the OMG
        // check functions (`coherent_sets_w_instances`,
        // `test_ordered_access_*`) use these lines to delimit one read of the
        // Subscriber and count the samples in between. One marker per reader
        // would cut every set into `num_topics` pieces.
        if opts.coherent {
            println!("Reading coherent sets");
        }
        if opts.ordered {
            println!("Reading with ordered access");
        }
        if access_bracket {
            subscriber.begin_access()?;
        }
        for rctx in &readers {
            rctx.reader.drive_listeners();
            // `srcCxx/shape_main.cxx` drains each reader with an inner
            // `do { take } while (retval == OK)` before moving to the next
            // topic, so one iteration presents everything that had arrived.
            // A non-consuming plain `read()` would never empty, so that one
            // case reads once.
            let drain = !(use_plain && opts.use_read);
            loop {
                let samples = if use_plain {
                    if opts.use_read {
                        rctx.reader.read_with_info()
                    } else {
                        rctx.reader.take_with_info()
                    }
                } else {
                    next_instance_batch(&rctx.reader, &rctx.prev_instance, opts.use_read)
                };
                let Ok(samples) = samples else {
                    break;
                };
                for s in &samples {
                    print_sample(&rctx.topic_name, s);
                }
                if !drain || samples.is_empty() {
                    break;
                }
            }
        }
        if access_bracket {
            let _ = subscriber.end_access();
        }
        iteration += 1;
        pace(&mut next_read, read_period);
    }
    Ok(())
}

/// `take_next_instance`/`read_next_instance`, cycling through every known
/// instance once per call (README default subscriber behaviour, absent
/// `--take-read`).
///
/// **Known upstream quirk** (see crate README "Known runtime quirks"):
/// `DataReader::{take,read}_next_instance` resolve the next instance via
/// `InstanceTracker::next_handle_after` *before* draining the incoming
/// sample channel into the cache (that drain — `ingest_into_cache` — only
/// runs inside `take_instance`/`read_instance`, which are never reached if
/// `next_handle_after` already returns `None`). On a reader that has never
/// called a plain `take`/`read`/`*_with_info` yet, the instance tracker is
/// still empty, so the very first `take_next_instance(HANDLE_NIL)` always
/// returns an empty `Vec` — even with data already in flight. A
/// non-consuming `read_with_info()` call forces that same ingestion path
/// as a side effect without disturbing the cache for the following
/// `take_next_instance`/`read_next_instance` call, so we do exactly that
/// once per poll tick before resolving the next instance. This is an
/// app-level workaround; the shared `crates/dcps` fix (call
/// `ingest_into_cache()` unconditionally at the top of
/// `take_next_instance`/`read_next_instance`, ahead of the
/// `next_handle_after` lookup) is out of scope for this binary's isolated
/// worktree and is called out for a separate fix.
fn next_instance_batch(
    reader: &DataReader<ShapeType>,
    prev: &Cell<InstanceHandle>,
    use_read: bool,
) -> zerodds_dcps::Result<Vec<Sample<ShapeType>>> {
    let _ = reader.read_with_info();
    let previous = prev.get();
    let out = if use_read {
        reader.read_next_instance(previous)
    } else {
        reader.take_next_instance(previous)
    };
    match &out {
        Ok(samples) => {
            if let Some(last) = samples.last() {
                prev.set(last.info.instance_handle);
            } else {
                prev.set(HANDLE_NIL);
            }
        }
        Err(_) => prev.set(HANDLE_NIL),
    }
    out
}

/// Sleeps until `deadline`, then advances it by `period`.
///
/// The README's `--write-period` / `--read-period` are the period of the loop,
/// not the pause after its body: sleeping a flat `period` at the end adds the
/// body's own cost to every cycle. With four instances and a flushed line per
/// sample that drift was measured at ~32 ms on a 100 ms write period, which is
/// enough to change what a 400 ms reader sees per tick — the OMG
/// `test_ordered_access_*` checks count exactly that. A deadline that moves by
/// a fixed period holds the cadence; if the body already overran it, the next
/// cycle starts immediately and the deadline is re-based on now so the loop
/// cannot accumulate a backlog.
fn pace(deadline: &mut std::time::Instant, period: StdDuration) {
    let now = std::time::Instant::now();
    if *deadline > now {
        std::thread::sleep(*deadline - now);
        *deadline += period;
    } else {
        *deadline = now + period;
    }
}

/// OMG `additional_payload_size` (`sequence<uint8>`): the filler the publisher
/// puts in every sample, exactly `n` octets long and empty for `n == 0`.
///
/// The reference client (`srcCxx/shape_main.cxx`) writes 255 into every
/// element, and `test_suite_functions.py::test_large_data` fails the case
/// unless the LAST element the subscriber prints is 255 — that is how the
/// harness proves the whole fragmented payload arrived intact.
fn payload_filler(n: usize) -> Vec<u8> {
    vec![255u8; n]
}

/// Formats the exact `basic_check`-compatible sample line
/// (`<topic> <color> <x> <y> [<shapesize>]`), or a lifecycle-marker line for a
/// dispose/unregister sample (`valid_data == false`).
///
/// A sample whose `additional_payload_size` sequence is non-empty gets the
/// reference client's ` {<last payload byte>}` suffix
/// (`srcCxx/shape_main.cxx`): `test_suite_functions.py::test_large_data` reads
/// exactly that number and requires 255, which is how the harness proves the
/// whole fragmented payload arrived intact. A sample without the sequence
/// prints the plain line every other check function expects.
fn sample_line(topic: &str, s: &Sample<ShapeType>) -> String {
    if !s.info.valid_data {
        let state = match s.info.instance_state {
            InstanceStateKind::NotAliveDisposed => "NOT_ALIVE_DISPOSED_INSTANCE_STATE",
            InstanceStateKind::NotAliveNoWriters => "NOT_ALIVE_NO_WRITERS_INSTANCE_STATE",
            InstanceStateKind::Alive => "ALIVE_INSTANCE_STATE",
        };
        return format!("{topic:<10} {:<10} {state}", s.data.color);
    }
    let head = format!(
        "{topic:<10} {:<10} {:03} {:03} [{}]",
        s.data.color, s.data.x, s.data.y, s.data.shapesize
    );
    match s.data.additional_payload_size.last() {
        Some(last) => format!("{head} {{{last}}}"),
        None => head,
    }
}

/// Prints the exact `basic_check`-compatible sample line
/// (`<topic> <color> <x> <y> [<shapesize>]`), or a lifecycle-marker line
/// for a dispose/unregister sample (`valid_data == false`).
fn print_sample(topic: &str, s: &Sample<ShapeType>) {
    println!("{}", sample_line(topic, s));
    // Flush each received-sample line for the pexpect-driven harness (same
    // real-time-read rationale as the writer-side flush).
    let _ = std::io::stdout().flush();
}

#[cfg(test)]
#[allow(clippy::expect_used, clippy::unwrap_used, clippy::panic)]
mod tests {
    use super::*;

    /// OMG `dds-rtps` `srcCxx/shape.idl` declares the fifth member as
    /// `sequence<uint8> additional_payload_size`, and the README's
    /// `--additional-payload-size <bytes>` sets how many extra bytes each
    /// sample carries. The clause is about the wire: the sequence LENGTH the
    /// sample puts on the wire is the requested byte count, and that many
    /// octets follow it.
    ///
    /// The layout (`interop/shapes/omg-dds-rtps.idl`, XCDR2-LE, `@appendable`):
    /// DHEADER, `color.length`, color bytes + NUL, padding, `x`, `y`,
    /// `shapesize`, `additional_payload_size.length`, elements.
    #[test]
    fn additional_payload_size_sets_the_sequence_length_on_the_wire() {
        for requested in [0usize, 1, 16, 1000] {
            let sample = ShapeType::with_payload("BLUE", 100, 100, 30, vec![0u8; requested]);
            let mut buf = Vec::new();
            DdsType::encode(&sample, &mut buf).expect("encode");

            // "BLUE" + NUL = 5 octets, padded to 8 -> the three int32s start at
            // 4 (DHEADER) + 4 (length) + 8 = 16.
            let seq_len_at = 4 + 4 + 8 + 12;
            let len = u32::from_le_bytes([
                buf[seq_len_at],
                buf[seq_len_at + 1],
                buf[seq_len_at + 2],
                buf[seq_len_at + 3],
            ]) as usize;
            assert_eq!(
                len, requested,
                "additional_payload_size.length must be the requested byte count"
            );
            assert_eq!(
                buf.len() - (seq_len_at + 4),
                requested,
                "exactly {requested} filler octets follow the length"
            );
        }
    }

    /// The sequence is always on the wire, length 0 when the flag is unset —
    /// a peer that reads the five-member `@appendable` form must not have to
    /// guess whether the member is present.
    #[test]
    fn additional_payload_size_zero_still_writes_the_length_field() {
        let sample = ShapeType::new("BLUE", 1, 2, 3);
        let mut buf = Vec::new();
        DdsType::encode(&sample, &mut buf).expect("encode");
        let seq_len_at = 4 + 4 + 8 + 12;
        assert_eq!(
            buf.len(),
            seq_len_at + 4,
            "the length field is the last 4 octets"
        );
        assert_eq!(&buf[seq_len_at..], &[0, 0, 0, 0]);
    }

    /// The publisher's filler is deterministic and exactly as long as
    /// requested — the harness's `LargeData` cases compare sample sizes.
    #[test]
    fn publisher_filler_is_deterministic_and_exactly_as_long_as_requested() {
        let opts = Options::try_parse_from(["shape_main", "-P", "--additional-payload-size", "64"])
            .expect("parse");
        let filler = payload_filler(opts.additional_payload_size as usize);
        assert_eq!(filler.len(), 64);
        assert_eq!(payload_filler(0), Vec::<u8>::new());
    }

    /// `test_suite_functions.py::test_large_data` matches
    /// `\w+\s+\w+\s+[0-9]+\s+[0-9]+\s+\[[0-9]+\]\s+\{([0-9]+)\}` on the
    /// subscriber's output and fails the case unless the captured number is
    /// 255 — the last octet of the `additional_payload_size` sequence, which
    /// only survives if the whole fragmented payload arrived. A sample with no
    /// payload keeps the plain line every other check function matches.
    #[test]
    fn sample_line_appends_the_last_payload_byte_only_when_there_is_a_payload() {
        use zerodds_dcps::sample_info::SampleInfo;

        let info = SampleInfo {
            valid_data: true,
            ..SampleInfo::default()
        };
        let with_payload = Sample::new(
            ShapeType::with_payload("BLUE", 10, 20, 30, vec![255u8; 100_000]),
            info,
        );
        assert_eq!(
            sample_line("Square", &with_payload),
            "Square     BLUE       010 020 [30] {255}"
        );

        let plain = Sample::new(ShapeType::new("BLUE", 10, 20, 30), info);
        assert_eq!(
            sample_line("Square", &plain),
            "Square     BLUE       010 020 [30]"
        );
    }

    /// The reference client (`srcCxx/shape_main.cxx`) writes 255 into every
    /// element of the payload sequence. A zero filler still has the right
    /// length, so the length check above passes — but `test_large_data` then
    /// reads `{0}` instead of `{255}` and fails the case.
    #[test]
    fn publisher_payload_filler_is_the_reference_clients_255() {
        let filler = payload_filler(16);
        assert!(filler.iter().all(|b| *b == 255));
        let sample = ShapeType::with_payload("BLUE", 1, 2, 30, filler);
        assert_eq!(sample.additional_payload_size.last(), Some(&255u8));
    }

    /// The suite's settings apply over the runtime's defaults, and a setting
    /// the environment names keeps the value the environment gave it.
    #[test]
    fn the_suite_settings_apply_unless_the_environment_names_them() {
        let mut config = RuntimeConfig::default();
        suite_settings(&mut config, |_| false);
        assert!(config.accept_empty_acknack_base_zero);
        assert_eq!(
            config.pl_cdr1_reading,
            zerodds_ast_layout::PlCdr1Reading::Tolerant
        );
        assert!(!config.writer_unregister_on_delete);
        assert!(!config.reader_honor_data_max_size_serialized);
        assert!(!config.reader_dispose_with_unregister);
        assert_eq!(
            config.key_member_bounds,
            zerodds_types::assignability::KeyMemberBounds::Ignored
        );

        let defaults = RuntimeConfig::default();
        let mut config = RuntimeConfig::default();
        suite_settings(&mut config, |_| true);
        assert_eq!(
            config.accept_empty_acknack_base_zero,
            defaults.accept_empty_acknack_base_zero
        );
        assert_eq!(config.pl_cdr1_reading, defaults.pl_cdr1_reading);
        assert_eq!(
            config.writer_unregister_on_delete,
            defaults.writer_unregister_on_delete
        );
        assert_eq!(
            config.reader_honor_data_max_size_serialized,
            defaults.reader_honor_data_max_size_serialized
        );
        assert_eq!(
            config.reader_dispose_with_unregister,
            defaults.reader_dispose_with_unregister
        );
        assert_eq!(config.key_member_bounds, defaults.key_member_bounds);
    }
}
