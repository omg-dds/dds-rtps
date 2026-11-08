// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 ZeroDDS Contributors

//! The suite's `ShapeType`, generated at build time from
//! `interop/shapes/omg-dds-rtps.idl`.
//!
//! It used to come from `zerodds_dcps::interop`, written by hand. A
//! suite run has to measure what this project generates: with the hand
//! form, a defect in the generator cannot fail the suite, and a defect
//! in the hand form is charged to us. Both happened — the hand-written
//! type left `DdsType::type_object()` at its default `None` (a topic
//! type name announced with no type behind it, no `PID_TYPE_INFORMATION`
//! in SEDP, XTypes 1.3 §7.6.3.2) and did not override
//! `encode_be`/`decode_be`, so a big-endian writer stamped `D_CDR2_BE`
//! onto a little-endian body.
//!
//! The hand form stays where it is. It is the second path of
//! `crates/dcps/tests/shapes_type_idl_agreement.rs`, which holds the
//! octets of both against each other in all four modes — that is what
//! it is good for, and it is not good for being the thing under test.

// `dead_code` is this binary's: the generated text is a type's whole
// surface — `key_hash`, the IDL's constants — and a binary that uses
// part of it leaves the rest unused. The clippy lints the generator used
// to trip here are gone from its output.
#[allow(dead_code)]
mod generated {
    include!(concat!(env!("OUT_DIR"), "/omg-dds-rtps.rs"));
}

pub use generated::ShapeType;

impl ShapeType {
    /// A shape with no filler payload — the ordinary sample.
    ///
    /// The generated type carries the five members and their codec and
    /// nothing else, which is the point of it. These two constructors
    /// are the client's convenience and touch no wire decision: the
    /// fifth member is written either way, with length zero here.
    #[must_use]
    pub fn new(color: impl Into<String>, x: i32, y: i32, shapesize: i32) -> Self {
        Self {
            color: color.into(),
            x,
            y,
            shapesize,
            additional_payload_size: Vec::new(),
        }
    }

    /// A shape whose fifth member carries `--additional-payload-size`
    /// octets of filler, for the suite's large-data runs.
    #[must_use]
    pub fn with_payload(
        color: impl Into<String>,
        x: i32,
        y: i32,
        shapesize: i32,
        additional_payload_size: Vec<u8>,
    ) -> Self {
        Self {
            color: color.into(),
            x,
            y,
            shapesize,
            additional_payload_size,
        }
    }
}

#[cfg(test)]
#[allow(clippy::expect_used, clippy::unwrap_used, clippy::panic)]
mod tests {
    use super::ShapeType;
    use zerodds_dcps::DdsType;

    /// The type this client measures with announces itself.
    ///
    /// This is the regression guard for the reason the type is generated
    /// at all. `DdsType::type_object()` defaults to `None`, and the
    /// hand-written `ShapeType` in `crates/dcps/src/interop.rs` takes
    /// that default: an endpoint built on it registers no `TypeObject`
    /// with the participant's TypeLookup server and its SEDP
    /// announcement carries no `PID_TYPE_INFORMATION` (XTypes 1.3
    /// §7.6.3.2) — a topic type name with no type behind it. Anyone who
    /// points this client back at the hand form fails here.
    #[test]
    fn the_measured_type_announces_a_type_object() {
        assert!(
            <ShapeType as DdsType>::type_object().is_some(),
            "the type this client measures with announces no TypeObject; \
             it is the hand-written one again, not the generated one"
        );
    }

    /// Big-endian is its own encoding, not little-endian with a
    /// different stamp.
    ///
    /// The other half of the same regression: the hand-written type did
    /// not override `encode_be`, so the `DdsType` default delegated to
    /// the little-endian body while the writer stamped `D_CDR2_BE`
    /// (RTPS 2.5 §10.5 — the representation identifier covers the whole
    /// payload). A peer then reads the DHEADER of a 24-octet sample as
    /// 402 653 184, and both sides stay quiet about it.
    #[test]
    fn the_two_byte_orders_do_not_produce_the_same_octets() {
        let sample = ShapeType::new("RED", 42, 77, 30);
        let mut le = Vec::new();
        DdsType::encode(&sample, &mut le).expect("little-endian encode");
        let mut be = Vec::new();
        DdsType::encode_be(&sample, &mut be).expect("big-endian encode");
        assert_ne!(
            le, be,
            "encode_be returned the little-endian octets; the big-endian \
             body would go out under a D_CDR2_BE stamp"
        );
        assert_eq!(le.len(), be.len(), "the two orders write the same length");
    }
}
