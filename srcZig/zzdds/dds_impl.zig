//! ZenzenDDS implementation of the srcZig/dds shim protocol.
//!
//! shape_main.zig imports this module as "dds".  Every symbol exported here
//! matches the protocol documented in srcZig/dds.zig; see that file for the
//! full contract that any Zig DDS vendor must satisfy.

const std = @import("std");

const zzdds = @import("zzdds");
const zzdds_gen = @import("zzdds_generated");

pub const DDS = zzdds_gen.DDS;

const UdpTransport = zzdds.udp_transport.UdpTransport;
const SpdpSedpDiscovery = zzdds.combined_discovery.SpdpSedpDiscovery;
const DomainParticipantFactoryImpl = zzdds.dcps.DomainParticipantFactoryImpl;
const DomainParticipantImpl = zzdds.dcps.DomainParticipantImpl;
const DataWriterImpl = zzdds.dcps.DataWriterImpl;
const DataReaderImpl = zzdds.dcps.DataReaderImpl;
const TopicImpl = zzdds.dcps.TopicImpl;
const ContentFilteredTopicImpl = zzdds.dcps.ContentFilteredTopicImpl;
const noop_security = zzdds.noop_security.noop_security_plugins;
const time_mod = zzdds.util.time;
const history_mod = zzdds.rtps.history;
const nil = zzdds.dcps;
const filter_mod = zzdds.dcps.filter;

// ── Participant bootstrapping ─────────────────────────────────────────────────

pub const Participant = struct {
    alloc: std.mem.Allocator,
    udp: *UdpTransport,
    disc: *SpdpSedpDiscovery,
    factory: *DomainParticipantFactoryImpl,
    dp: DDS.DomainParticipant,

    pub fn toDDS(self: *Participant) DDS.DomainParticipant {
        return self.dp;
    }
};

pub fn createParticipant(alloc: std.mem.Allocator, domain_id: u32) !*Participant {
    const p = try alloc.create(Participant);
    errdefer alloc.destroy(p);

    const udp = try UdpTransport.init(alloc, .{}, domain_id, null);
    errdefer udp.deinit();
    const transport = udp.transport();

    const disc = try SpdpSedpDiscovery.init(alloc, transport, domain_id, 3_000);
    errdefer disc.deinit();
    const discovery = disc.toDiscovery();

    var factory = try DomainParticipantFactoryImpl.init(
        alloc,
        transport,
        discovery,
        noop_security,
        .spec_random,
        .{},
    );
    errdefer factory.deinit();
    const dpf = factory.toDDSFactory();

    const dp = dpf.create_participant(domain_id, .{}, nil.nil_dp_listener, 0);
    if (dp.ptr == nil.nil_dp_listener.ptr) return error.ParticipantFailed;

    p.* = .{
        .alloc = alloc,
        .udp = udp,
        .disc = disc,
        .factory = factory,
        .dp = dp,
    };
    return p;
}

pub fn destroyParticipant(p: *Participant) void {
    const dpf = p.factory.toDDSFactory();
    _ = dpf.delete_participant(p.dp);
    p.factory.deinit();
    p.disc.deinit();
    p.udp.deinit();
    p.alloc.destroy(p);
}

// ── Topic name ────────────────────────────────────────────────────────────────

pub fn topicName(topic: DDS.Topic) []const u8 {
    const impl: *TopicImpl = @ptrCast(@alignCast(topic.ptr));
    return impl.topic_name;
}

// ── DataWriter extras ─────────────────────────────────────────────────────────

pub const WriteKind = enum { alive, dispose, unregister };

pub fn writeRaw(
    dw: DDS.DataWriter,
    kind: WriteKind,
    key_hash: [16]u8,
    data: []const u8,
) !void {
    const impl: *DataWriterImpl = @ptrCast(@alignCast(dw.ptr));
    const ck: history_mod.ChangeKind = switch (kind) {
        .alive => .alive,
        .dispose => .not_alive_disposed,
        .unregister => .not_alive_unregistered,
    };
    _ = try impl.writeRaw(ck, time_mod.RtpsTimestamp.now(), history_mod.INSTANCE_HANDLE_NIL, key_hash, data);
}

pub fn writerMatchedCount(dw: DDS.DataWriter) usize {
    const impl: *DataWriterImpl = @ptrCast(@alignCast(dw.ptr));
    return impl.matchedReaderCount();
}

pub fn writerNotifyDeadline(dw: DDS.DataWriter) void {
    const impl: *DataWriterImpl = @ptrCast(@alignCast(dw.ptr));
    impl.notifyDeadlineMissed();
}

// ── DataReader extras ─────────────────────────────────────────────────────────

pub const TakenSample = struct {
    data: []u8,
    alloc: std.mem.Allocator,
    instance_state: DDS.InstanceStateKind,

    pub fn deinit(self: TakenSample) void {
        self.alloc.free(self.data);
    }
};

pub fn takeRaw(dr: DDS.DataReader) ?TakenSample {
    const impl: *DataReaderImpl = @ptrCast(@alignCast(dr.ptr));
    const taken = impl.takeRaw() orelse return null;
    return .{
        .data = taken.data,
        .alloc = impl.alloc,
        .instance_state = taken.info.instance_state,
    };
}

pub fn readerMatchedCount(dr: DDS.DataReader) usize {
    const impl: *DataReaderImpl = @ptrCast(@alignCast(dr.ptr));
    return impl.matchedWriterCount();
}

pub fn readerNotifyDeadline(dr: DDS.DataReader) void {
    const impl: *DataReaderImpl = @ptrCast(@alignCast(dr.ptr));
    impl.notifyDeadlineMissed();
}

// ── ContentFilteredTopic evaluation ──────────────────────────────────────────

pub const FilterValue = filter_mod.FilterValue;
pub const FieldAccessor = filter_mod.FieldAccessor;

pub fn cftMatchSample(cft: DDS.ContentFilteredTopic, acc: FieldAccessor) bool {
    const impl: *ContentFilteredTopicImpl = @ptrCast(@alignCast(cft.ptr));
    return impl.matchSample(acc);
}

pub fn cftTopicDescription(cft: DDS.ContentFilteredTopic) DDS.TopicDescription {
    const impl: *ContentFilteredTopicImpl = @ptrCast(@alignCast(cft.ptr));
    return impl.toTopicDescription();
}

// ── TypeSupport ───────────────────────────────────────────────────────────────

pub const TypeSupport = zzdds.dcps.TypeSupport;

pub fn registerTypeSupport(
    dp: DDS.DomainParticipant,
    type_name: []const u8,
    ts: TypeSupport,
) void {
    const impl: *DomainParticipantImpl = @ptrCast(@alignCast(dp.ptr));
    impl.registerTypeSupport(type_name, ts);
}

// ── ShapeType CDR ─────────────────────────────────────────────────────────────
//
// ShapeType CDR serialization uses zidl-generated code from srcZig/shape.idl.
// The generated module (shape_gen) handles all CDR encoding details.

const shape_gen = @import("shape_gen");
const zidl_rt = @import("zidl_rt");

/// Wrapper type for shape_main.zig.  Keeps a borrowed `color` slice (valid
/// while the source payload is alive) and separates the publisher-side
/// `additional_payload` size from the subscriber-side `last_payload_byte`.
pub const ShapeType = struct {
    color: []const u8,
    x: i32 = 0,
    y: i32 = 0,
    shapesize: i32 = 20,
    additional_payload: u32 = 0,
    last_payload_byte: ?u8 = null,
};

/// Serialize shape into `buf` (cleared first) using zidl-generated CDR.
/// xcdr2=false → CDR_LE (0x0001); xcdr2=true → CDR2_LE (0x0007) with DHEADER.
pub fn serializeShape(
    buf: *std.ArrayList(u8),
    alloc: std.mem.Allocator,
    s: ShapeType,
    xcdr2: bool,
) !void {
    // Build a temporary generated ShapeType for the serializer.
    var shape: shape_gen.ShapeType = .{
        .color = zidl_rt.BoundedArray(u8, 128).fromSlice(s.color) catch return error.ColorTooLong,
        .x = s.x,
        .y = s.y,
        .shapesize = s.shapesize,
    };
    if (s.additional_payload > 0) {
        try shape.additional_payload_size.ensureTotalCapacity(alloc, s.additional_payload);
        for (0..s.additional_payload - 1) |_|
            shape.additional_payload_size.appendAssumeCapacity(0);
        shape.additional_payload_size.appendAssumeCapacity(255);
    }
    defer shape.additional_payload_size.deinit(alloc);

    buf.clearRetainingCapacity();
    if (xcdr2) {
        var w = zidl_rt.CdrWriter(.xcdr2).init(buf, alloc);
        try w.writeEncapHeader();
        try shape_gen.ShapeType.serialize(&w, shape);
    } else {
        var w = zidl_rt.CdrWriter(.xcdr1).init(buf, alloc);
        try w.writeEncapHeader();
        try shape_gen.ShapeType.serialize(&w, shape);
    }
}

/// Serialize a key-only CDR payload (XCDR1) for dispose/unregister writes.
pub fn serializeShapeKeyOnly(
    buf: *std.ArrayList(u8),
    alloc: std.mem.Allocator,
    color: []const u8,
) !void {
    const shape = shape_gen.ShapeType{
        .color = zidl_rt.BoundedArray(u8, 128).fromSlice(color) catch return error.ColorTooLong,
    };
    buf.clearRetainingCapacity();
    var w = zidl_rt.CdrWriter(.xcdr1).init(buf, alloc);
    try w.writeEncapHeader();
    try shape_gen.ShapeType.serializeKey(&w, shape);
}

/// Deserialize a CDR/CDR2 ShapeType payload.  Returns null on parse error or
/// if the payload is key-only (missing x/y/shapesize).  The returned color
/// slice is zero-copied from `payload` and is valid only while `payload` lives.
pub fn deserializeShape(payload: []const u8) ?ShapeType {
    var reader = zidl_rt.CdrReader.init(payload) catch return null;
    reader.skipDheaderIfXcdr2() catch return null;
    const color = reader.readStringZeroCopy() catch return null;
    if (color.len > 128) return null;
    const x = reader.readI32() catch return null;
    const y = reader.readI32() catch return null;
    const shapesize = reader.readI32() catch return null;
    const extra_len = reader.readU32() catch 0;
    var last_byte: ?u8 = null;
    if (extra_len > 0) {
        reader.skip(extra_len - 1) catch {};
        last_byte = reader.readU8() catch null;
    }
    return .{
        .color = color,
        .x = x,
        .y = y,
        .shapesize = shapesize,
        .additional_payload = extra_len,
        .last_payload_byte = last_byte,
    };
}

/// Extract the color key string from a CDR payload (full or key-only).
/// Zero-copied from `payload`; valid only while `payload` is alive.
pub fn deserializeShapeKey(payload: []const u8) []const u8 {
    var reader = zidl_rt.CdrReader.init(payload) catch return "";
    reader.skipDheaderIfXcdr2() catch return "";
    return reader.readStringZeroCopy() catch "";
}

/// Compute the RTPS key hash for a ShapeType instance from its color string.
/// Delegates to the generated computeKeyHash which uses zidl_rt.KeyHashWriter
/// (CDR_BE, MD5 fallback for keys > 16 bytes).
pub fn shapeKeyHash(color: []const u8) [16]u8 {
    const shape = shape_gen.ShapeType{
        .color = zidl_rt.BoundedArray(u8, 128).fromSlice(color) catch return std.mem.zeroes([16]u8),
    };
    return shape_gen.ShapeType.computeKeyHash(shape);
}

/// Compute the RTPS key hash from a received CDR payload.
/// Suitable for use as TypeSupport.compute_key_hash.
pub fn shapeKeyHashFromCdr(payload: []const u8) [16]u8 {
    return shapeKeyHash(deserializeShapeKey(payload));
}

// ── Nil sentinel helpers ──────────────────────────────────────────────────────
// All nil entities share the same underlying nil_storage address (NIL_PTR).
// We recover that address from any exported nil constant without needing to
// re-export NIL_PTR itself.

fn nilPtr() *anyopaque {
    return zzdds.dcps.nil_topic_listener.ptr;
}

pub fn nilTopicListener() DDS.TopicListener {
    return zzdds.dcps.nil_topic_listener;
}
pub fn nilPublisherListener() DDS.PublisherListener {
    return zzdds.dcps.nil_pub_listener;
}
pub fn nilSubscriberListener() DDS.SubscriberListener {
    return zzdds.dcps.nil_sub_listener;
}

pub fn isNilDp(dp: DDS.DomainParticipant) bool {
    return dp.ptr == nilPtr();
}
pub fn isNilTopic(t: DDS.Topic) bool {
    return t.ptr == nilPtr();
}
pub fn isNilPub(p: DDS.Publisher) bool {
    return p.ptr == nilPtr();
}
pub fn isNilSub(s: DDS.Subscriber) bool {
    return s.ptr == nilPtr();
}
pub fn isNilDw(dw: DDS.DataWriter) bool {
    return dw.ptr == nilPtr();
}
pub fn isNilDr(dr: DDS.DataReader) bool {
    return dr.ptr == nilPtr();
}
pub fn isNilCft(cft: DDS.ContentFilteredTopic) bool {
    return cft.ptr == nilPtr();
}
