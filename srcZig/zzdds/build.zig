const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const LogLevel = enum { err, warn, info, debug };

    const version = b.option([]const u8, "dds-version", "Full zzdds version string for the executable name (e.g. 0.1.0-zig.0.16.0); omit for a stable CI-friendly name");
    const sanitize_thread = b.option(bool, "sanitize-thread", "Enable ThreadSanitizer (requires libc, Linux only)") orelse false;
    const debug_allocator = b.option(bool, "debug-allocator", "Route the factory's allocation path through std.heap.DebugAllocator instead of the default std.heap.c_allocator, for fast attributable double-free/UAF diagnostics") orelse false;
    const default_log_level: LogLevel = switch (optimize) {
        .Debug => .debug,
        .ReleaseSafe, .ReleaseFast, .ReleaseSmall => .info,
    };
    const log_level = b.option(LogLevel, "log-level", "shape_main std.log level: err, warn, info, debug (default matches Zig build mode)") orelse default_log_level;

    const zzdds_dep = b.dependency("zzdds", .{ .target = target, .optimize = optimize, .@"sanitize-thread" = sanitize_thread });
    const zzdds_mod = zzdds_dep.module("zzdds");
    const zzdds_gen = zzdds_dep.module("zzdds_generated");

    // Use zzdds's generator and runtime modules to share type identity.
    const zidl_exe = zzdds_dep.artifact("zidl");
    const runtime_imports: []const std.Build.Module.Import = if (zzdds_dep.builder.modules.get("zidl_cdr")) |codec|
        &.{ .{ .name = "zidl_cdr", .module = codec }, .{ .name = "zidl_bindings", .module = zzdds_dep.module("zidl_bindings") } }
    else
        &.{.{ .name = "zidl_rt", .module = zzdds_dep.module("zidl_rt") }};

    // Build the "dds" shim module from our vendor implementation.
    // dds_impl.zig provides participant bootstrapping and entity-management
    // helpers.  CDR encoding is handled by the generated typed wrappers.
    const dds_impl_options = b.addOptions();
    dds_impl_options.addOption(bool, "debug_allocator", debug_allocator);

    const dds_mod = b.createModule(.{
        .root_source_file = b.path("dds_impl.zig"),
        .target = target,
        .optimize = optimize,
        .sanitize_thread = sanitize_thread,
        .imports = &.{
            .{ .name = "zzdds", .module = zzdds_mod },
            .{ .name = "zzdds_generated", .module = zzdds_gen },
            .{ .name = "dds_impl_options", .module = dds_impl_options.createModule() },
        },
    });

    // Generate ShapeType Zig bindings from srcZig/shape.idl.
    // The generated shape.zig uses ShapeTypeDataWriter/ShapeTypeDataReader which
    // call into dds_mod via @import("dds").  Output lands in the build cache.
    const gen_shape = b.addRunArtifact(zidl_exe);
    gen_shape.addArgs(&.{ "-b", "zig", "--split-files", "--generate-zzdds-wrappers", "-o" });
    const shape_gen_dir = gen_shape.addOutputDirectoryArg("shape-generated");
    gen_shape.addFileArg(b.path("../shape.idl"));

    const shape_gen_mod = b.createModule(.{
        .root_source_file = shape_gen_dir.path(b, "shape.zig"),
        .target = target,
        .optimize = optimize,
        .sanitize_thread = sanitize_thread,
        .imports = &.{
            .{ .name = "zzdds", .module = zzdds_mod },
        },
    });

    for (runtime_imports) |runtime| shape_gen_mod.addImport(runtime.name, runtime.module);

    const exe_name = if (version) |v|
        std.fmt.allocPrint(b.allocator, "zzdds-{s}_shape_main_linux", .{v}) catch @panic("OOM")
    else
        "zzdds_shape_main_linux";
    const shape_main_options = b.addOptions();
    shape_main_options.addOption([]const u8, "log_level", @tagName(log_level));

    const exe = b.addExecutable(.{
        .name = exe_name,
        .root_module = b.createModule(.{
            .root_source_file = b.path("../shape_main.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{
                .{ .name = "dds", .module = dds_mod },
                .{ .name = "shape_gen", .module = shape_gen_mod },
                .{ .name = "shape_main_options", .module = shape_main_options.createModule() },
            },
        }),
        // Zig 0.16's self-hosted backend silently no-ops sanitize_thread
        // without this (confirmed empirically upstream in zzdds's own
        // build.zig) -- force the LLVM backend whenever TSan is requested.
        .use_llvm = if (sanitize_thread) true else null,
    });
    for (runtime_imports) |runtime| exe.root_module.addImport(runtime.name, runtime.module);
    exe.root_module.link_libc = true;
    exe.root_module.sanitize_thread = sanitize_thread;
    b.installArtifact(exe);

    const run_step = b.step("run", "Run shape_main");
    const run_cmd = b.addRunArtifact(exe);
    run_cmd.addPassthruArgs();
    run_step.dependOn(&run_cmd.step);
}
