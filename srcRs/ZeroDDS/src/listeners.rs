// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 ZeroDDS Contributors
//! Lifecycle listener that prints the **exact** stdout strings the
//! `dds-rtps` `interoperability_report.py` / `test_suite.py` harness
//! `pexpect`-matches.
//!
//! Every string below was extracted from the live
//! `github.com/omg-dds/dds-rtps` source (`interoperability_report.py`
//! `run_publisher_shape_main` / `run_subscriber_shape_main`,
//! `test_suite_functions.py`) and cross-validated against both committed
//! Rust reference clients (`srcRs/DustDDS`, `srcRs/HDDS`). Do not
//! paraphrase or reformat these — a one-character deviation breaks the
//! harness's `pexpect.expect([...])` matching:
//!
//! - `"Create topic:"` (publisher **and** subscriber)
//! - `"Create writer for topic"` (publisher; **no** trailing colon)
//! - `"Create reader for topic:"` (subscriber; **with** trailing colon)
//! - `"failed to create content filtered topic"`
//! - `"on_publication_matched()"`
//! - `"on_offered_incompatible_qos"` (harness matches the bare substring;
//!   we still print the full `on_offered_incompatible_qos()` — it
//!   contains the substring)
//! - `"on_offered_deadline_missed()"`
//! - `"on_requested_incompatible_qos()"`
//! - `"on_requested_deadline_missed()"`
//! - `"on_subscription_matched()"` (not `pexpect`-checked by the core
//!   interoperability_report.py flow, but printed for spec completeness
//!   — mirrors both Rust reference clients)
//! - sample line: `<topic> <color> <x> <y> [<shapesize>]` — matched by
//!   `rtps_test_utilities.py` `basic_check`'s
//!   `r'\w\s+\w+\s+[0-9]+ [0-9]+ \[([0-9]+)\]'`.

#![allow(clippy::print_stdout)]

use std::sync::atomic::{AtomicU64, Ordering};

use zerodds_dcps::InstanceHandle;
use zerodds_dcps::listener::{DataReaderListener, DataWriterListener};
use zerodds_dcps::psm_constants::qos_policy_id;
use zerodds_dcps::status::{
    LivelinessChangedStatus, LivelinessLostStatus, OfferedDeadlineMissedStatus,
    OfferedIncompatibleQosStatus, PublicationMatchedStatus, QosPolicyCount,
    RequestedDeadlineMissedStatus, RequestedIncompatibleQosStatus, SubscriptionMatchedStatus,
};

/// Human name for a `qos_policy_id` — used only in the diagnostic suffix
/// of the incompatible-QoS lines; the harness only checks the leading
/// `on_*_incompatible_qos` literal, not this suffix.
fn policy_name(id: u32) -> &'static str {
    match id {
        qos_policy_id::USER_DATA => "USER_DATA",
        qos_policy_id::DURABILITY => "DURABILITY",
        qos_policy_id::PRESENTATION => "PRESENTATION",
        qos_policy_id::DEADLINE => "DEADLINE",
        qos_policy_id::LATENCY_BUDGET => "LATENCY_BUDGET",
        qos_policy_id::OWNERSHIP => "OWNERSHIP",
        qos_policy_id::OWNERSHIP_STRENGTH => "OWNERSHIP_STRENGTH",
        qos_policy_id::LIVELINESS => "LIVELINESS",
        qos_policy_id::TIME_BASED_FILTER => "TIME_BASED_FILTER",
        qos_policy_id::PARTITION => "PARTITION",
        qos_policy_id::RELIABILITY => "RELIABILITY",
        qos_policy_id::DESTINATION_ORDER => "DESTINATION_ORDER",
        qos_policy_id::HISTORY => "HISTORY",
        qos_policy_id::RESOURCE_LIMITS => "RESOURCE_LIMITS",
        qos_policy_id::DATA_REPRESENTATION => "DATA_REPRESENTATION",
        _ => "UNKNOWN",
    }
}

fn last_policy(status_last_id: u32, policies: &[QosPolicyCount]) -> String {
    let count = policies
        .iter()
        .find(|p| p.policy_id == status_last_id)
        .map_or(0, |p| p.count);
    format!("{} (count={count})", policy_name(status_last_id))
}

/// One instance per DataWriter **and** per DataReader (the two trait
/// impls below share the struct — the listener callbacks only ever get
/// an opaque `InstanceHandle`, so the topic/type names have to be
/// captured at construction time, same as any per-entity listener).
pub struct ShapeListener {
    topic_name: String,
    type_name: &'static str,
    matched: AtomicU64,
}

impl ShapeListener {
    #[must_use]
    pub fn new(topic_name: impl Into<String>, type_name: &'static str) -> Self {
        Self {
            topic_name: topic_name.into(),
            type_name,
            matched: AtomicU64::new(0),
        }
    }
}

impl DataWriterListener for ShapeListener {
    fn on_offered_deadline_missed(
        &self,
        _writer: InstanceHandle,
        status: OfferedDeadlineMissedStatus,
    ) {
        println!(
            "on_offered_deadline_missed() topic: '{}'  type: '{}' : (total = {}, change = {})",
            self.topic_name, self.type_name, status.total_count, status.total_count_change
        );
    }

    fn on_offered_incompatible_qos(
        &self,
        _writer: InstanceHandle,
        status: OfferedIncompatibleQosStatus,
    ) {
        if is_synthetic_first_poll_qos(status.total_count, status.total_count_change) {
            return;
        }
        println!(
            "on_offered_incompatible_qos() topic: '{}'  type: '{}' : {}",
            self.topic_name,
            self.type_name,
            last_policy(status.last_policy_id, &status.policies)
        );
    }

    fn on_liveliness_lost(&self, _writer: InstanceHandle, status: LivelinessLostStatus) {
        println!(
            "on_liveliness_lost() topic: '{}'  type: '{}' : (total = {}, change = {})",
            self.topic_name, self.type_name, status.total_count, status.total_count_change
        );
    }

    fn on_publication_matched(&self, _writer: InstanceHandle, status: PublicationMatchedStatus) {
        if is_synthetic_first_poll_match(status.total_count, status.total_count_change) {
            return;
        }
        self.matched
            .store(status.current_count.max(0) as u64, Ordering::Relaxed);
        println!(
            "on_publication_matched() topic: '{}'  type: '{}' : matched readers {} (change = {})",
            self.topic_name, self.type_name, status.current_count, status.current_count_change
        );
    }
}

impl DataReaderListener for ShapeListener {
    fn on_requested_deadline_missed(
        &self,
        _reader: InstanceHandle,
        status: RequestedDeadlineMissedStatus,
    ) {
        println!(
            "on_requested_deadline_missed() topic: '{}'  type: '{}' : (total = {}, change = {})",
            self.topic_name, self.type_name, status.total_count, status.total_count_change
        );
    }

    fn on_requested_incompatible_qos(
        &self,
        _reader: InstanceHandle,
        status: RequestedIncompatibleQosStatus,
    ) {
        if is_synthetic_first_poll_qos(status.total_count, status.total_count_change) {
            return;
        }
        println!(
            "on_requested_incompatible_qos() topic: '{}'  type: '{}' : {}",
            self.topic_name,
            self.type_name,
            last_policy(status.last_policy_id, &status.policies)
        );
    }

    fn on_liveliness_changed(&self, _reader: InstanceHandle, status: LivelinessChangedStatus) {
        println!(
            "on_liveliness_changed() topic: '{}'  type: '{}' : (alive = {}, not_alive = {})",
            self.topic_name, self.type_name, status.alive_count, status.not_alive_count
        );
    }

    fn on_subscription_matched(&self, _reader: InstanceHandle, status: SubscriptionMatchedStatus) {
        if is_synthetic_first_poll_match(status.total_count, status.total_count_change) {
            return;
        }
        self.matched
            .store(status.current_count.max(0) as u64, Ordering::Relaxed);
        println!(
            "on_subscription_matched() topic: '{}'  type: '{}' : matched writers {} (change = {})",
            self.topic_name, self.type_name, status.current_count, status.current_count_change
        );
    }
}

/// `PUBLICATION_MATCHED`/`SUBSCRIPTION_MATCHED` are poll-based
/// (`crates/dcps/src/publisher.rs` `poll_publication_matched`,
/// `crates/dcps/src/subscriber.rs` analogue): the delta tracker starts at
/// a `-1` "never polled" sentinel, so the very first `drive_listeners()`
/// call *always* reports a transition — even with zero real matches and
/// zero real change. That synthetic event is exactly, and only,
/// identifiable by `total_count == 0 && total_count_change == 0`: the
/// dispatch path returns early whenever `prev == curr` (see
/// `poll_publication_matched`), so every *other* call that reaches this
/// listener represents a genuine transition, and a genuine transition can
/// never leave a monotonically-accumulating `total_count` at `0`.
///
/// We could instead "prime" the tracker with a throwaway pre-listener
/// poll, but that races a real match that completes before the priming
/// call runs (observed locally on loopback: the poll would silently eat a
/// real first match). Filtering on the synthetic event's own signature
/// has no such race — see `tools/omg-shape-main/README.md` "Known runtime
/// quirks".
const fn is_synthetic_first_poll_match(total_count: i32, total_count_change: i32) -> bool {
    total_count == 0 && total_count_change == 0
}

/// Same reasoning as [`is_synthetic_first_poll_match`], applied to
/// `OFFERED_INCOMPATIBLE_QOS`/`REQUESTED_INCOMPATIBLE_QOS`
/// (`poll_offered_incompatible_qos` and its reader-side analogue): a real
/// incompatibility can never leave `total_count` at `0`.
const fn is_synthetic_first_poll_qos(total_count: i32, total_count_change: i32) -> bool {
    total_count == 0 && total_count_change == 0
}
