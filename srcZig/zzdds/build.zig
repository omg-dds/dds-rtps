const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const LogLevel = enum { err, warn, info, debug };

    const version = b.option([]const u8, "dds-version", "Full zzdds version string for the executable name (e.g. 0.1.0-zig.0.16.0); omit for a stable CI-friendly name");
    const sanitize_thread = b.option(bool, "sanitize-thread", "Enable ThreadSanitizer (requires libc, Linux only)") orelse false;
    const default_log_level: LogLevel = switch (optimize) {
        .Debug => .debug,
        .ReleaseSafe, .ReleaseFast, .ReleaseSmall => .info,
    };
    const log_level = b.option(LogLevel, "log-level", "shape_main std.log level: err, warn, info, debug (default matches Zig build mode)") orelse default_log_level;

    const zzdds_dep = b.dependency("zzdds", .{ .target = target, .optimize = optimize });
    const zzdds_mod = zzdds_dep.module("zzdds");
    const zzdds_gen = zzdds_dep.module("zzdds_generated");

    // Acquire zidl executable and zidl_rt module from the zidl dependency.
    const zidl_dep = b.dependency("zidl", .{ .target = target, .optimize = optimize });
    const zidl_exe = zidl_dep.artifact("zidl");
    const zidl_rt_mod = zidl_dep.module("zidl_rt");

    // Generate ShapeType Zig bindings from srcZig/shape.idl.
    // Output lands in the build cache (not checked in).
    const gen_shape = b.addRunArtifact(zidl_exe);
    gen_shape.addArgs(&.{ "-b", "zig", "--split-files", "-o" });
    const shape_gen_dir = gen_shape.addOutputDirectoryArg("shape-generated");
    gen_shape.addFileArg(b.path("../shape.idl"));

    const shape_gen_mod = b.createModule(.{
        .root_source_file = shape_gen_dir.path(b, "shape.zig"),
        .target = target,
        .optimize = optimize,
        .imports = &.{
            .{ .name = "zidl_rt", .module = zidl_rt_mod },
        },
    });

    // Build the "dds" shim module from our vendor implementation.
    // shape_main.zig imports only this module; it has no direct zzdds dependency.
    const dds_mod = b.createModule(.{
        .root_source_file = b.path("dds_impl.zig"),
        .target = target,
        .optimize = optimize,
        .imports = &.{
            .{ .name = "zzdds", .module = zzdds_mod },
            .{ .name = "zzdds_generated", .module = zzdds_gen },
            .{ .name = "shape_gen", .module = shape_gen_mod },
            .{ .name = "zidl_rt", .module = zidl_rt_mod },
        },
    });

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
                .{ .name = "shape_main_options", .module = shape_main_options.createModule() },
            },
        }),
    });
    exe.root_module.link_libc = true;
    exe.root_module.sanitize_thread = sanitize_thread;
    b.installArtifact(exe);

    const run_step = b.step("run", "Run shape_main");
    const run_cmd = b.addRunArtifact(exe);
    if (b.args) |args| run_cmd.addArgs(args);
    run_step.dependOn(&run_cmd.step);
}
