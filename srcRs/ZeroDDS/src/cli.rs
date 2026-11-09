// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 ZeroDDS Contributors
//! CLI flag surface for the OMG `dds-rtps` interoperability-test-suite
//! `shape_main` reference client.
//!
//! The flag set + short/long spellings below are transcribed **verbatim**
//! from `github.com/omg-dds/dds-rtps` `README.md` ("Shape Application
//! parameters" section), cross-validated against the two committed Rust
//! reference implementations in that repo (`srcRs/DustDDS/src/main.rs`,
//! `srcRs/HDDS/src/main.rs`) — both independently reproduce the same flag
//! names, so this is the canonical set the `interoperability_report.py` /
//! `test_suite.py` harness feeds via `'apps': ['-P -t Square -r ...', ...]`
//! parameter strings.
//!
//! A handful of short-letter aliases (`-i`, `-l`, `-n`, `-I`, `-E`, `-M`,
//! `-C`, `-T`, `-O`, `-H`, `-B`, `-K`) are **not** in the README table
//! itself but appear in both Rust reference implementations' `clap`/manual
//! parsers; we mirror them for drop-in compatibility with hand-typed
//! invocations, but the test suite always uses the long form.
//!
//! `--cft <expr>` is a vendor extension (mirrored from DustDDS/HDDS, not
//! in the README table) needed so the harness's
//! `'failed to create content filtered topic'` pexpect alternative has
//! something to trigger against.

use clap::{Parser, ValueEnum};

/// `-D [v|l|t|p]` — durability kind letters, exactly as in the README.
#[derive(Copy, Clone, Debug, PartialEq, Eq, ValueEnum)]
pub enum DurabilityArg {
    /// `v` — VOLATILE.
    V,
    /// `l` — TRANSIENT_LOCAL.
    L,
    /// `t` — TRANSIENT.
    T,
    /// `p` — PERSISTENT.
    P,
}

/// `--access-scope [i|t|g]` — PresentationQosPolicy.access_scope.
#[derive(Copy, Clone, Debug, PartialEq, Eq, ValueEnum)]
pub enum AccessScopeArg {
    /// `i` — INSTANCE (default).
    I,
    /// `t` — TOPIC.
    T,
    /// `g` — GROUP.
    G,
}

/// `--final-instance-state [u|d]` — action after the DataWriter's last
/// write, before the writer is torn down.
#[derive(Copy, Clone, Debug, PartialEq, Eq, ValueEnum)]
pub enum FinalInstanceStateArg {
    /// `u` — `unregister_instance`.
    U,
    /// `d` — `dispose`.
    D,
}

/// `-v [e|d]` — log verbosity. `e` (and the absent flag) print errors
/// only; `d` additionally prints per-step diagnostics. Every diagnostic
/// goes to **stderr**, so the harness's `pexpect` matching against stdout
/// stays byte-identical between the two levels.
#[derive(Copy, Clone, Debug, PartialEq, Eq, ValueEnum)]
pub enum VerbosityArg {
    /// `e` — ERROR only (the default).
    E,
    /// `d` — DEBUG (verbose).
    D,
}

/// OMG `dds-rtps` `shape_main` — ZeroDDS reference client.
///
/// Flag documentation strings below are the README's own wording (kept
/// verbatim where practical) so `--help` output stays diffable against
/// the upstream table.
#[derive(Parser, Debug, Clone)]
#[command(name = "shape_main", author, version, about, long_about = None, args_override_self = true)]
pub struct Options {
    /// `-v [e|d]`: set log message verbosity.
    #[arg(short = 'v', value_enum)]
    pub verbosity: Option<VerbosityArg>,

    /// `-P`: publish samples.
    #[arg(short = 'P')]
    pub publish: bool,

    /// `-S`: subscribe samples.
    #[arg(short = 'S')]
    pub subscribe: bool,

    /// `-d <int>`: domain id (default: 0).
    #[arg(short = 'd', default_value_t = 0)]
    pub domain_id: i32,

    /// `-b`: BEST_EFFORT reliability.
    #[arg(short = 'b', conflicts_with = "reliable")]
    pub best_effort: bool,

    /// `-r`: RELIABLE reliability, also the default without `-b`
    /// (`qos_map::reliability`).
    #[arg(short = 'r')]
    pub reliable: bool,

    /// `-k <depth>`: keep history depth (`0` = KEEP_ALL).
    #[arg(short = 'k', allow_negative_numbers = false)]
    pub history_depth: Option<i32>,

    /// `-f <interval>`: DEADLINE interval in ms (`0` = OFF).
    #[arg(short = 'f', default_value_t = 0)]
    pub deadline_ms: i64,

    /// `-s <strength>`: OwnershipStrength (`-1` = SHARED ownership).
    #[arg(short = 's', allow_negative_numbers = true, default_value_t = -1)]
    pub ownership_strength: i32,

    /// `-t <topic_name>`: the topic name.
    #[arg(short = 't', default_value = "Square")]
    pub topic_name: String,

    /// `-c <color>`: color to publish (filter, if subscriber).
    #[arg(short = 'c')]
    pub color: Option<String>,

    /// `-p <partition>`: a 'partition' string.
    #[arg(short = 'p')]
    pub partition: Option<String>,

    /// `-D [v|l|t|p]`: durability.
    #[arg(short = 'D', value_enum)]
    pub durability: Option<DurabilityArg>,

    /// `-x [1|2]`: data representation (1: XCDR, 2: XCDR2).
    #[arg(short = 'x')]
    pub data_representation: Option<u8>,

    /// `-w`: print Publisher's samples.
    #[arg(short = 'w')]
    pub print_writer_samples: bool,

    /// `-z <int>`: shapesize (`0` = increase the size for every sample).
    #[arg(short = 'z', default_value_t = 30)]
    pub shapesize: i32,

    /// `--size-modulo <uint>`: with `-z 0`, wrap the increasing shapesize
    /// sequence modulo N (`1, 2, …, N, 1, 2, …`). `0` (default) = no wrap
    /// (`1, 2, 3, …`). Ignored when `-z != 0`. Some official test cases pass
    /// this flag; accepting it lets their shape_main client start.
    ///
    /// Non-negative by type: a negative value is a hard clap parse error, not
    /// a silent "disabled".
    #[arg(long = "size-modulo", default_value_t = 0)]
    pub size_modulo: u32,

    /// `-R`: use `read()` instead of `take()`.
    #[arg(short = 'R')]
    pub use_read: bool,

    /// `--write-period <ms>`: waiting period between `write()` calls.
    #[arg(long = "write-period", default_value_t = 33)]
    pub write_period_ms: u64,

    /// `--read-period <ms>`: waiting period between `read()`/`take()` calls.
    #[arg(long = "read-period", default_value_t = 100)]
    pub read_period_ms: u64,

    /// `--time-filter <interval>`: TIME_BASED_FILTER interval in ms
    /// (`0` = OFF). Short alias `-i` (DustDDS convention).
    #[arg(long = "time-filter", short = 'i', default_value_t = 0)]
    pub time_filter_ms: i64,

    /// `--lifespan <int>`: LIFESPAN of a sample in ms. Short alias `-l`.
    #[arg(long = "lifespan", short = 'l', default_value_t = 0)]
    pub lifespan_ms: i64,

    /// `--num-iterations <int>`: iterations of the main loop before exit
    /// (default: infinite). Short alias `-n`.
    #[arg(long = "num-iterations", short = 'n')]
    pub num_iterations: Option<u64>,

    /// `--num-instances <int>`: number of instances a DataWriter writes
    /// (color, color1, color2, ...). Short alias `-I`.
    #[arg(long = "num-instances", short = 'I', default_value_t = 1)]
    pub num_instances: u32,

    /// `--num-topics <int>`: number of topics created (Square, Square1,
    /// Square2, ...), one DataWriter/DataReader each. Short alias `-E`.
    #[arg(long = "num-topics", short = 'E', default_value_t = 1)]
    pub num_topics: u32,

    /// `--final-instance-state [u|d]`: action after the DataWriter
    /// finishes, before it is torn down. Short alias `-M`.
    #[arg(long = "final-instance-state", short = 'M', value_enum)]
    pub final_instance_state: Option<FinalInstanceStateArg>,

    /// `--access-scope [i|t|g]`: Presentation.access_scope. Short alias
    /// `-C`.
    #[arg(long = "access-scope", short = 'C', value_enum)]
    pub access_scope: Option<AccessScopeArg>,

    /// `--coherent`: Presentation.coherent_access = true. Short alias
    /// `-T`.
    #[arg(long = "coherent", short = 'T')]
    pub coherent: bool,

    /// `--ordered`: Presentation.ordered_access = true. Short alias `-O`.
    #[arg(long = "ordered", short = 'O')]
    pub ordered: bool,

    /// `--coherent-sample-count <int>`: samples per coherent set, per
    /// DataWriter+instance. Short alias `-H`.
    #[arg(long = "coherent-sample-count", short = 'H', default_value_t = 0)]
    pub coherent_sample_count: u32,

    /// `--additional-payload-size <bytes>`: extra bytes appended to each
    /// sample (large-data tests). Short alias `-B`.
    ///
    /// Maps to the OMG `shape.idl` member `sequence<uint8>
    /// additional_payload_size`: the writer fills the sequence with this
    /// many filler bytes, so its length equals the requested payload size
    /// on the wire (`crates/dcps/src/interop.rs` `ShapeType`).
    #[arg(long = "additional-payload-size", short = 'B', default_value_t = 0)]
    pub additional_payload_size: u32,

    /// `--take-read`: use `take()`/`read()` instead of
    /// `take_next_instance()`/`read_next_instance()`. Short alias `-K`.
    #[arg(long = "take-read", short = 'K')]
    pub take_read: bool,

    /// `--periodic-announcement <ms>`: participant announcement period
    /// (`0` = off / use the ZeroDDS runtime default SPDP cadence).
    #[arg(long = "periodic-announcement", default_value_t = 0)]
    pub periodic_announcement_ms: u32,

    /// `--cft <expr>`: content-filter expression for the subscriber's
    /// reader (vendor extension, mirrors DustDDS/HDDS `--cft`; not in
    /// the README flag table). SQL-92 subset per `zerodds-sql-filter`
    /// (DDS-DCPS Annex B).
    #[arg(long = "cft")]
    pub cft: Option<String>,
}

impl Options {
    /// Resolved color: `-c` if given, else the ShapesDemo canonical
    /// default `"BLUE"`.
    #[must_use]
    pub fn resolved_color(&self) -> &str {
        self.color.as_deref().unwrap_or("BLUE")
    }

    /// `-v d` — debug verbosity is on. `-v e` and the absent flag are
    /// error-only.
    #[must_use]
    pub fn debug_verbosity(&self) -> bool {
        matches!(self.verbosity, Some(VerbosityArg::D))
    }

    /// Number of samples per coherent set and per DataWriter+instance
    /// (`--coherent-sample-count`, README wording). `0` — the flag's default
    /// — means one sample per set, which is the smallest set the writer can
    /// form. Only meaningful together with `--coherent`.
    #[must_use]
    pub fn coherent_set_size(&self) -> u32 {
        self.coherent_sample_count.max(1)
    }
}

#[cfg(test)]
#[allow(clippy::expect_used, clippy::unwrap_used, clippy::panic)]
mod tests {
    use super::*;

    fn parse(args: &[&str]) -> Options {
        Options::try_parse_from(args).expect("parse")
    }

    /// OMG `dds-rtps` README, `-v [e|d]`: the flag sets the log verbosity.
    /// `d` is the only value that turns diagnostics on.
    #[test]
    fn verbosity_debug_only_for_d() {
        assert!(parse(&["shape_main", "-P", "-v", "d"]).debug_verbosity());
        assert!(!parse(&["shape_main", "-P", "-v", "e"]).debug_verbosity());
        assert!(!parse(&["shape_main", "-P"]).debug_verbosity());
    }

    /// `-v` rejects any letter outside the README's `[e|d]` set instead of
    /// accepting it and ignoring it.
    #[test]
    fn verbosity_rejects_unknown_letter() {
        assert!(Options::try_parse_from(["shape_main", "-P", "-v", "x"]).is_err());
    }

    /// README `--coherent-sample-count <int>`: samples per coherent set, per
    /// DataWriter+instance. The unset default forms one-sample sets.
    #[test]
    fn coherent_set_size_defaults_to_one() {
        assert_eq!(parse(&["shape_main", "-P"]).coherent_set_size(), 1);
        assert_eq!(
            parse(&["shape_main", "-P", "--coherent-sample-count", "4"]).coherent_set_size(),
            4
        );
        assert_eq!(
            parse(&["shape_main", "-P", "-H", "7"]).coherent_set_size(),
            7
        );
    }

    /// OMG `srcCxx/shape.idl`: `sequence<uint8> additional_payload_size`.
    /// `-B <bytes>` is the sequence length the writer puts on the wire.
    #[test]
    fn additional_payload_size_is_parsed_as_byte_count() {
        assert_eq!(parse(&["shape_main", "-P"]).additional_payload_size, 0);
        assert_eq!(
            parse(&["shape_main", "-P", "--additional-payload-size", "1024"])
                .additional_payload_size,
            1024
        );
        assert_eq!(
            parse(&["shape_main", "-P", "-B", "16"]).additional_payload_size,
            16
        );
    }
}
