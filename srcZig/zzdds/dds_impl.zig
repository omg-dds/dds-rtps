//! ZenzenDDS implementation used by shape_main.zig.
//!
//! shape_main.zig imports this module as "dds".  Provides participant
//! bootstrapping and the DDS entity-management helpers used by shape_main.zig.
//! CDR serialization lives in the zidl-generated shape.zig (shape_gen module);
//! the generated ShapeTypeDataWriter/DataReader import zzdds directly.

const std = @import("std");

const zzdds = @import("zzdds");
const zzdds_gen = @import("zzdds_generated");
const build_options = @import("dds_impl_options");

pub const DDS = zzdds_gen.DDS;

const DomainParticipantImpl = zzdds.dcps.DomainParticipantImpl;
const TopicImpl = zzdds.dcps.TopicImpl;
const ContentFilteredTopicImpl = zzdds.dcps.ContentFilteredTopicImpl;
const nil = zzdds.dcps;

// ── Participant bootstrapping ─────────────────────────────────────────────────

pub const Participant = struct {
    alloc: std.mem.Allocator,
    /// Only populated (and only referenced by `factory`) when
    /// build_options.debug_allocator is set -- must live exactly as long as
    /// `factory` does, hence stored here rather than as a temporary in
    /// createParticipant: a ZidlAllocator built as a local in the function
    /// that calls createFactoryWithAllocator would leave the factory holding
    /// a dangling pointer the moment that function returns (see
    /// createFactoryWithAllocator's own doc comment in zzdds).
    c_alloc: zzdds.c_abi.allocator_adapter.ZidlAllocator = undefined,
    factory: zzdds.DomainParticipantFactory,
    dp: DDS.DomainParticipant,

    pub fn toDDS(self: *Participant) DDS.DomainParticipant {
        return self.dp;
    }
};

/// RTPS-level tunables with no standard DCPS QoS equivalent -- see dds.zig's
/// contract doc for the "0 = leave the vendor default alone" convention.
pub const ParticipantOptions = struct {
    fragment_size: u16 = 0,
    announcement_period_ms: u32 = 0,
};

pub fn createParticipant(alloc: std.mem.Allocator, domain_id: u32, opts: ParticipantOptions) !*Participant {
    const p = try alloc.create(Participant);
    errdefer alloc.destroy(p);
    p.alloc = alloc;

    var factory = if (build_options.debug_allocator) blk: {
        p.c_alloc = zzdds.c_abi.allocator_adapter.fromAllocator(&p.alloc);
        break :blk try zzdds.createFactoryWithAllocator(&p.c_alloc);
    } else try zzdds.createFactory();
    errdefer factory.deinit();

    const dp = if (opts.fragment_size > 0 or opts.announcement_period_ms > 0) blk: {
        // Starts from the plain IDL-declared defaults (`.{}`), not the
        // factory's current default_participant_config: this shim has no
        // other way to customize the factory's defaults before this call
        // (unlike zzdds-examples' zig/shape, which also supports --config),
        // so there is nothing else to preserve. Deliberately does NOT use
        // get_default_participant_config/set_default_participant_config --
        // those don't exist yet at the zzdds release this build.zig.zon pins
        // (added later, in "Config File Improvements" (#54)); only
        // create_participant_ex is guaranteed present.
        var cfg: zzdds.ZZDDS.DomainParticipantConfig = .{};
        if (opts.fragment_size > 0) cfg.rtps.fragment_size = opts.fragment_size;
        if (opts.announcement_period_ms > 0) cfg.participant.announcement_period_ms = opts.announcement_period_ms;
        break :blk factory.toZZDDSFactory().create_participant_ex(domain_id, .{}, null, 0, cfg);
    } else factory.toDDSFactory().create_participant(domain_id, .{}, null, 0);
    if (dp.ptr == nil.NIL_PTR) return error.ParticipantFailed;

    // Field-by-field, not a `p.* = .{...}` struct literal: that would reset
    // c_alloc to its `undefined` default, corrupting the ZidlAllocator the
    // factory (already constructed above) is holding a live pointer into.
    p.factory = factory;
    p.dp = dp;
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
