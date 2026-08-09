//! ZenzenDDS implementation used by shape_main.zig.
//!
//! shape_main.zig imports this module as "dds".  Provides participant
//! bootstrapping and the DDS entity-management helpers used by shape_main.zig.
//! CDR serialization lives in the zidl-generated shape.zig (shape_gen module);
//! the generated ShapeTypeDataWriter/DataReader import zzdds directly.

const std = @import("std");

const zzdds = @import("zzdds");
const zzdds_gen = @import("zzdds_generated");

pub const DDS = zzdds_gen.DDS;

const DomainParticipantImpl = zzdds.dcps.DomainParticipantImpl;
const TopicImpl = zzdds.dcps.TopicImpl;
const ContentFilteredTopicImpl = zzdds.dcps.ContentFilteredTopicImpl;
const nil = zzdds.dcps;

// ── Participant bootstrapping ─────────────────────────────────────────────────

pub const Participant = struct {
    alloc: std.mem.Allocator,
    factory: zzdds.DomainParticipantFactory,
    dp: DDS.DomainParticipant,

    pub fn toDDS(self: *Participant) DDS.DomainParticipant {
        return self.dp;
    }
};

pub fn createParticipant(alloc: std.mem.Allocator, domain_id: u32) !*Participant {
    const p = try alloc.create(Participant);
    errdefer alloc.destroy(p);

    var factory = try zzdds.createFactory();
    errdefer factory.deinit();
    const dpf = factory.toDDSFactory();

    const dp = dpf.create_participant(domain_id, .{}, null, 0);
    if (dp.ptr == nil.NIL_PTR) return error.ParticipantFailed;

    p.* = .{
        .alloc = alloc,
        .factory = factory,
        .dp = dp,
    };
    return p;
}

pub fn destroyParticipant(p: *Participant) void {
    const dpf = p.factory.toDDSFactory();
    _ = dpf.delete_participant(p.dp);
    p.factory.deinit();
    p.alloc.destroy(p);
}

// ── Topic name ────────────────────────────────────────────────────────────────

pub fn topicName(topic: DDS.Topic) []const u8 {
    const impl: *TopicImpl = @ptrCast(@alignCast(topic.ptr));
    return impl.topic_name;
}

// ── DataWriter extras ─────────────────────────────────────────────────────────

pub fn writerWaitForAck(dw: DDS.DataWriter, timeout: DDS.Duration_t) DDS.ReturnCode_t {
    return dw.vtable.wait_for_acknowledgments(dw.ptr, &timeout);
}

pub fn writerMatchedCount(dw: DDS.DataWriter) usize {
    var status: DDS.PublicationMatchedStatus = .{};
    _ = dw.vtable.get_publication_matched_status(dw.ptr, &status);
    return @intCast(status.current_count);
}

// ── DataReader extras ─────────────────────────────────────────────────────────

pub fn readerMatchedCount(dr: DDS.DataReader) usize {
    var status: DDS.SubscriptionMatchedStatus = .{};
    _ = dr.vtable.get_subscription_matched_status(dr.ptr, &status);
    return @intCast(status.current_count);
}

// ── ContentFilteredTopic ──────────────────────────────────────────────────────
// Filtering itself is automatic, at the reader layer, once TypeSupport.get_field
// is wired (see registerTypeSupport's call site in shape_main.zig)

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
    _ = impl.registerTypeSupport(type_name, ts);
}

// ── Nil sentinel helpers ──────────────────────────────────────────────────────
// All nil entities share the same underlying nil_storage address (NIL_PTR).

pub fn nilTopicListener() DDS.TopicListener {
    return DDS.noop_TopicListener;
}
pub fn nilPublisherListener() DDS.PublisherListener {
    return DDS.noop_PublisherListener;
}
pub fn nilSubscriberListener() DDS.SubscriberListener {
    return DDS.noop_SubscriberListener;
}

pub fn isNilDp(dp: DDS.DomainParticipant) bool {
    return dp.ptr == zzdds.dcps.NIL_PTR;
}
pub fn isNilTopic(t: DDS.Topic) bool {
    return t.ptr == zzdds.dcps.NIL_PTR;
}
pub fn isNilPub(p: DDS.Publisher) bool {
    return p.ptr == zzdds.dcps.NIL_PTR;
}
pub fn isNilSub(s: DDS.Subscriber) bool {
    return s.ptr == zzdds.dcps.NIL_PTR;
}
pub fn isNilDw(dw: DDS.DataWriter) bool {
    return dw.ptr == zzdds.dcps.NIL_PTR;
}
pub fn isNilDr(dr: DDS.DataReader) bool {
    return dr.ptr == zzdds.dcps.NIL_PTR;
}
pub fn isNilCft(cft: DDS.ContentFilteredTopic) bool {
    return cft.ptr == zzdds.dcps.NIL_PTR;
}
