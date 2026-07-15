//! Zig DDS shim — interface contract for srcZig/shape_main.zig.
//!
//! shape_main.zig imports a module named "dds".  Any Zig DDS vendor that
//! wants to participate in the dds-rtps interoperability test suite provides
//! their own implementation of this module and wires it up as the "dds"
//! dependency in their build.zig.
//!
//! ZenzenDDS's implementation lives in zenzen-zig/dds_impl.zig.
//!
//! ── Required exports ──────────────────────────────────────────────────────
//!
//!   pub const DDS = ...;
//!     Re-export of the vendor's standard DDS type package.  Must expose the
//!     standard DCPS entity handles and QoS/Status types used by shape_main:
//!     DomainParticipant, Publisher, Subscriber, Topic, ContentFilteredTopic,
//!     TopicDescription, DataWriter, DataReader, DataWriterQos, DataReaderQos,
//!     PublisherQos, SubscriberQos, DataWriterListener, DataReaderListener,
//!     StatusMask, and the status constants (OFFERED_INCOMPATIBLE_QOS_STATUS,
//!     etc.).
//!
//!   pub const DDS = ...;
//!     The vendor's standard DCPS type package (see above).
//!
//!   -- Type aliases required by the zidl-generated ShapeTypeDataWriter /
//!   -- ShapeTypeDataReader (which call into this module as "_dds"):
//!
//!   pub const DataWriter = DDS.DataWriter;
//!   pub const DataReader = DDS.DataReader;
//!   pub const InstanceStateKind = DDS.InstanceStateKind;
//!   pub const InstanceHandle_t = DDS.InstanceHandle_t;
//!
//!   pub const Participant = struct { ... };
//!     Opaque vendor state that bundles transport, discovery, and factory.
//!     shape_main calls createParticipant / destroyParticipant and then
//!     calls toDDS() to get the standard DomainParticipant handle for use
//!     with the standard vtable API.
//!
//!   pub fn createParticipant(alloc: std.mem.Allocator, domain_id: u32) !*Participant;
//!   pub fn destroyParticipant(p: *Participant) void;
//!
//!   pub fn topicName(topic: DDS.Topic) []const u8;
//!     Returns the topic name string from a DDS.Topic handle.
//!
//!   ── Raw CDR write / read (used by ShapeTypeDataWriter, ShapeTypeDataReader,
//!   ── and directly by shape_main for NOT_ALIVE sample handling) ─────────────
//!
//!   pub const WriteKind = enum { alive, dispose, unregister };
//!
//!   pub fn writeCdr(dw: DDS.DataWriter, kind: WriteKind,
//!                   key_hash: [16]u8, data: []const u8) !void;
//!     Write a pre-serialized CDR payload.  The vendor stamps the source
//!     timestamp internally (always "now").  Called by the generated
//!     ShapeTypeDataWriter.write() / .dispose() / .unregister() methods.
//!
//!   pub const RawSample = struct {
//!       data:             []u8,
//!       alloc:            std.mem.Allocator,
//!       instance_state:   DDS.InstanceStateKind,
//!       instance_handle:  DDS.InstanceHandle_t,
//!       pub fn deinit(self: RawSample) void,
//!   };
//!
//!   pub fn takeCdr(dr: DDS.DataReader) ?RawSample;
//!     Returns the next pending sample, or null if the queue is empty.
//!     Caller must call sample.deinit() when done.
//!     Called by the generated ShapeTypeDataReader.take() and directly by
//!     shape_main for NOT_ALIVE sample key extraction.
//!
//!   pub fn writerWaitForAck(dw: DDS.DataWriter, timeout: DDS.Duration_t) DDS.ReturnCode_t;
//!   pub fn writerMatchedCount(dw: DDS.DataWriter) usize;
//!   pub fn writerNotifyDeadline(dw: DDS.DataWriter) void;
//!   pub fn readerMatchedCount(dr: DDS.DataReader) usize;
//!   pub fn readerNotifyDeadline(dr: DDS.DataReader) void;
//!
//!   ── ContentFilteredTopic evaluation ──────────────────────────────────
//!
//!   pub const FilterValue = union(enum) {
//!       string: []const u8,
//!       int:    i64,
//!       float:  f64,
//!   };
//!
//!   pub const FieldAccessor = struct {
//!       ctx: *anyopaque,
//!       get: *const fn (ctx: *anyopaque, field: []const u8) ?FilterValue,
//!   };
//!
//!   pub fn cftMatchSample(cft: DDS.ContentFilteredTopic, acc: FieldAccessor) bool;
//!   pub fn cftTopicDescription(cft: DDS.ContentFilteredTopic) DDS.TopicDescription;
//!
//!   ── TypeSupport (type schema registration) ────────────────────────────
//!
//!   pub const TypeSupport = struct {
//!       ctx:              *anyopaque,
//!       compute_key_hash: *const fn (ctx: *anyopaque, payload: []const u8) [16]u8,
//!   };
//!
//!   pub fn registerTypeSupport(dp: DDS.DomainParticipant,
//!                              type_name: []const u8,
//!                              ts: TypeSupport) void;
//!     Register a key-hash computation callback for a named type.  Call
//!     before creating DataReaders for that type so that received changes
//!     whose inline-QoS omits a key_hash can have one computed from the
//!     CDR payload.  `payload` passed to compute_key_hash includes the
//!     4-byte CDR encapsulation header.

// ── Module layout ─────────────────────────────────────────────────────────────
//
// CDR serialization and key-hash computation are NOT part of the "dds" shim.
// They live in the zidl-generated "shape_gen" module imported by shape_main.zig.
//
// The generated shape.zig emits ShapeTypeDataWriter and ShapeTypeDataReader
// which internally call into this module as "_dds" (via @import("dds")):
//   - ShapeTypeDataWriter.write()      → writeCdr(dw, .alive, hash, payload)
//   - ShapeTypeDataWriter.dispose()    → writeCdr(dw, .dispose, hash, key_payload)
//   - ShapeTypeDataWriter.unregister() → writeCdr(dw, .unregister, hash, key_payload)
//   - ShapeTypeDataReader.take()       → takeCdr(dr) + ShapeType.deserialize()
//
// shape_main.zig also calls takeCdr() directly to inspect instance_state
// before deserialization for NOT_ALIVE sample handling.

// This file is documentation only.  shape_main.zig imports the module
// named "dds" which is provided by the vendor's build.zig, not this file.
