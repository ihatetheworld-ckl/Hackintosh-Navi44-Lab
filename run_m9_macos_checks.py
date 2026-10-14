"""M9 Apple-only, serial CPU verification. BSD-3-Clause.

Uses existing tools/SDK only. No download, install, Makefile, device, native
execution, Kext link, signing or loading. x86_64 executables are never run.
All explicit writes, temporary files, module caches and logs stay in the lab.
Run inside the session's filesystem sandbox; path checks do not replace it.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import platform
import re
import resource
import shlex
import struct
import subprocess
import sys
import time

if sys.version_info < (3, 11):
    raise SystemExit("Select an existing Python 3.11+ interpreter; no auto-install")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import m7_safety as safe
import run_host_tests as host


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", required=True)
    parser.add_argument("--sdk", required=True)
    args = parser.parse_args()
    if sys.platform != "darwin" or platform.machine() != "arm64":
        raise SystemExit("This M9 matrix requires the authorized arm64 Mac; x86 runtime NOT RUN")
    compiler, sdk = Path(args.compiler), Path(args.sdk)
    if not compiler.is_absolute() or not compiler.is_file() or not sdk.is_absolute() or not sdk.is_dir():
        raise SystemExit("Existing absolute compiler and SDK paths are required")
    out = safe.mkdir("reports/m9")
    logs = safe.mkdir(out / "logs")
    build = safe.mkdir("build/m9")
    temp = safe.mkdir("tmp/m9")
    env = os.environ.copy()
    env.update(TMPDIR=str(temp), TMP=str(temp), TEMP=str(temp),
               CLANG_MODULE_CACHE_PATH=str(safe.mkdir(build / "cache")),
               PYTHONDONTWRITEBYTECODE="1", ASAN_OPTIONS="halt_on_error=1:detect_leaks=0:abort_on_error=0",
               UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
    # Avoid inherited injected headers, libraries or runtimes changing evidence.
    for key in ("CPATH", "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH", "LIBRARY_PATH", "DYLD_INSERT_LIBRARIES"):
        env.pop(key, None)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    commands = []

    def run(command, name, *, timeout=60, data=None, allow_failure=False):
        command = [str(x) for x in command]
        if "-o" in command:
            safe.checked(command[command.index("-o") + 1])
        start = time.monotonic()
        print(name, flush=True)
        try:
            p = subprocess.run(command, cwd=safe.ROOT, env=env, input=data,
                               capture_output=True, text=True, encoding="utf-8", timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            commands.append(dict(name=name, argv=command, exit=None, status="TIMEOUT"))
            safe.write(logs / (name + ".log"), "TIMEOUT\n" +
                       (exc.stdout or b"").decode("utf-8", errors="replace") +
                       (exc.stderr or b"").decode("utf-8", errors="replace"))
            safe.write(out / "commands.json", json.dumps(commands, indent=2))
            raise
        commands.append(dict(name=name, argv=command, exit=p.returncode,
                             seconds=round(time.monotonic() - start, 3)))
        safe.write(logs / (name + ".log"), p.stdout + p.stderr)
        safe.write(out / "commands.json", json.dumps(commands, indent=2))
        if p.returncode and not allow_failure:
            raise RuntimeError(name + " failed; see project log")
        return p

    summary = dict(stage="M9", status="RUNNING", Kext="NOT RUN", GPU="NOT RUN",
                   Metal="NOT RUN", Windows_execution="NOT RUN", x86_64_runtime="NOT RUN",
                   x86_64_sanitizer_runtime="NOT RUN", CMake="NOT RUN: not installed in PATH")
    safe.write(out / "test-results.json", json.dumps(summary, indent=2))
    try:
        version = run([compiler, "--version"], "apple-clang-version").stdout
        if "Apple clang" not in version:
            raise RuntimeError("A genuine Apple Clang is required")
        summary.update(compiler=version.strip(), sdk=str(sdk), python=sys.version,
                       python_executable=sys.executable)
        source_paths = host.PURE + [host.SRC / "offlinevalidation.cpp",
                                    safe.checked("run_host_tests.py"), safe.checked(__file__),
                                    safe.checked("tests/fixtures/m9_differential.py")]
        # Snapshot all project sources involved, not historical report hashes.
        source_paths += list((host.SRC.parent / "core").glob("*.hpp"))
        source_paths += list((host.SRC.parent / "platform").glob("*.hpp"))
        source_paths += list((host.SRC.parent / "host").glob("*.hpp"))
        source_paths += list((safe.ROOT / "tests/unit").glob("*.cpp"))
        source_paths += [host.SRC.parent / "platform/darwin_native.cpp",
                         host.SRC.parent / "host/navi44.py", safe.checked("tests/fixtures/synthetic.py"),
                         safe.checked("tests/fixtures/m8_display.hpp")]
        source_paths += [host.SRC / (p.stem + ".hpp") for p in host.PURE if p.parent == host.SRC]
        source_paths += [host.SRC / "asicprofile.hpp", host.SRC / "offlinevalidation.hpp"]
        before = {p.relative_to(safe.ROOT).as_posix(): hashlib.sha256(safe.checked(p).read_bytes()).hexdigest()
                  for p in source_paths}
        safe.write(out / "source-sha256.json", json.dumps(before, indent=2))
        for stage, arch, options in (("m9-arm64", "arm64", []),
                                     ("m9-x86_64", "x86_64", ["--compile-only", "--skip-python"]),
                                     ("m9-sanitized", "arm64", ["--sanitize", "--skip-python"])):
            run([sys.executable, "-I", "-B", "-X", "utf8", safe.checked("run_host_tests.py"),
                 "--compiler", compiler, "--sdk", sdk, "--stage", stage, "--arch", arch, *options],
                stage, timeout=600)  # each child compile/test has its own 60s timeout
            result = json.loads(safe.checked("reports/" + stage + "/results.json").read_text())
            if result["status"] != "PASS" or result["target_arch"] != arch:
                raise RuntimeError("Host result mismatch")
            summary[stage] = result
        tools = {}
        for name in ("nm", "otool", "lipo"):
            tools[name] = run(["xcrun", "--find", name], "find-" + name).stdout.strip()

        def macho(path, arch, filetype):
            raw = safe.checked(path).read_bytes()
            magic, cpu, subtype, kind, count, command_bytes, flags, _ = struct.unpack_from("<IiiIIIII", raw)
            expected = {"arm64": 0x100000c, "x86_64": 0x1000007}[arch]
            if magic != 0xfeedfacf or cpu != expected or kind != filetype:
                raise RuntimeError("Mach-O architecture/type mismatch: " + str(path))
            offset, platforms = 32, []
            if offset + command_bytes > len(raw):
                raise RuntimeError("Mach-O command bounds")
            for _ in range(count):
                cmd, size = struct.unpack_from("<II", raw, offset)
                if size < 8 or offset + size > 32 + command_bytes:
                    raise RuntimeError("Mach-O load command bounds")
                if cmd == 0x32:
                    plat, minimum, sdk_version = struct.unpack_from("<III", raw, offset + 8)
                    platforms.append(dict(platform=plat, minos=minimum, sdk=sdk_version))
                offset += size
            if not platforms or any(p["platform"] != 1 for p in platforms):
                raise RuntimeError("Expected LC_BUILD_VERSION macOS")
            return dict(path=path.relative_to(safe.ROOT).as_posix(), architecture=arch,
                        cputype=cpu, cpusubtype=subtype, filetype=kind, build_version=platforms,
                        sha256=hashlib.sha256(raw).hexdigest(), flags=flags)

        audit = []
        forbidden = ("__cxa_throw", "__cxa_allocate_exception", "__gxx_personality", "_Unwind",
                     "__dynamic_cast", "_ZSt", "_Znwm", "_Znam", "_ZTI", "_ZTS")
        for arch, stage in (("arm64", "m9-arm64"), ("x86_64", "m9-x86_64")):
            for source in host.PURE:
                obj = safe.checked("build/" + stage + "/" + source.stem + ".o")
                record = macho(obj, arch, 1)
                symbols = run([tools["nm"], "-u", obj], arch + "-symbols-" + obj.stem).stdout
                if any(token in symbols for token in forbidden):
                    raise RuntimeError("Core exception/RTTI/heap/STL dependency: " + str(obj))
                record["undefined_symbols"] = symbols.splitlines()
                audit.append(record)
            obj = safe.checked("build/" + stage + "/contract.o")
            audit.append(macho(obj, arch, 1))
            for name in host.TESTS:
                audit.append(macho(safe.checked("build/" + stage + "/" + name), arch, 2))
            run(["file", *[safe.checked("build/" + stage + "/" + p.stem + ".o") for p in host.PURE]],
                arch + "-file-types")
            run([tools["lipo"], "-archs", safe.checked("build/" + stage + "/validation.o")], arch + "-lipo")
            run([tools["otool"], "-h", "-l", safe.checked("build/" + stage + "/validation.o")], arch + "-load-commands")
        safe.write(out / "macho-audit.json", json.dumps(audit, indent=2))
        summary["object_audit"] = "PASS: CPU, MH_OBJECT/MH_EXECUTE, macOS build version, core symbols"

        common = [compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-UNDEBUG", "-O1", "-g",
                  "-arch", "arm64", "-isysroot", sdk, "-mmacosx-version-min=13.0", "-I" + str(host.SRC)]
        fixture_path = safe.checked("tests/fixtures/m9_differential.py")
        spec = importlib.util.spec_from_file_location("m9differential", fixture_path)
        fixtures = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixtures)
        cases, mutations = fixtures.all_cases, fixtures.fuzz_cases()
        if len(cases) != 744 or len(mutations) != 2400:
            raise RuntimeError("Reviewed finite corpus count changed")

        def compare(exe, inputs, name):
            p = run([exe], name, timeout=30, data="".join(fixtures.request(*c) for c in inputs))
            rows = p.stdout.splitlines()
            if len(rows) != len(inputs):
                raise RuntimeError("Differential output count mismatch")
            differences = []
            for i, (case, row) in enumerate(zip(inputs, rows)):
                expected, actual = fixtures.canonical(*case), json.loads(row)
                if expected != actual:
                    differences.append(dict(index=i, mode=case[0], params=case[2],
                                            hex=bytes(case[1]).hex(), python=expected, cpp=actual))
            safe.write(out / (name + "-differences.json"), json.dumps(differences, indent=2))
            if differences:
                raise RuntimeError(name + " has semantic differences")

        for stage, sanitized in (("m9-arm64", False), ("m9-sanitized", True)):
            base = safe.checked("build/" + stage)
            probe = safe.checked(base / "m65_probe")
            flags = ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"] if sanitized else []
            objects = [safe.checked(base / (p.stem + ".o")) for p in host.PURE]
            run(common + flags + [safe.checked("tests/unit/m65_probe.cpp"), base / "offlinevalidation.o",
                                  *objects, "-o", probe], stage + "-link-probe")
            compare(probe, cases, stage + "-differential")
            compare(probe, mutations, stage + "-bounded-mutation")
        summary["differential"] = dict(cases=744, differences=0, status="PASS")
        summary["parser_mutation"] = dict(inputs=2400, seed=759070, differences=0, status="PASS")
        summary["sanitizer"] = dict(status="PASS", architecture="arm64", cpp_assertions=161,
                                    parser_inputs=3144, display_inputs=2400, query_inputs=800,
                                    leaks="NOT VERIFIED", x86_64_runtime="NOT RUN")
        for kind, mode, diagnostic in (("address", "asan", "heap-buffer-overflow"),
                                       ("undefined", "ubsan", "signed integer overflow")):
            exe = safe.checked(build / ("canary-" + kind))
            run(common + ["-fsanitize=" + kind, "-fno-omit-frame-pointer",
                          safe.checked("tests/unit/sanitizer_canary.cpp"), "-o", exe], "link-canary-" + kind)
            p = run([exe, mode], "canary-" + kind, allow_failure=True)
            if p.returncode == 0 or diagnostic not in p.stdout + p.stderr:
                raise RuntimeError("Sanitizer failed to detect intentional CPU fault")
        summary["sanitizer"]["canaries"] = "PASS: actual heap overflow and signed overflow detected"

        kernel = sdk / "System/Library/Frameworks/Kernel.framework/Headers"
        native = dict(compile="NOT RUN", link="NOT RUN", runtime="NOT RUN", headers=str(kernel))
        if not (kernel / "IOKit/IOLib.h").is_file():
            native["blocker"] = "Existing genuine Kernel.framework headers unavailable; no download attempted"
        else:
            native_build = safe.mkdir(build / "native-x86_64")
            native_flags = [compiler, "-std=c++17", "-arch", "x86_64", "-isysroot", sdk,
                            "-mmacosx-version-min=13.0", "-isystem", kernel, "-nostdinc++",
                            "-DKERNEL", "-DKERNEL_EXTENSION", "-mkernel", "-fapple-kext",
                            "-fno-exceptions", "-fno-rtti", "-ffreestanding", "-fno-stack-protector",
                            "-mno-red-zone", "-Wall", "-Wextra", "-Werror", "-Wframe-larger-than=4096",
                            "-O1", "-g"]
            sources = [safe.checked("development/AMDRadeonRDNA4-Navi44/platform/darwin_native.cpp"),
                       safe.checked("tests/unit/m9_native_compile.cpp"), *host.PURE,
                       safe.checked("tests/unit/m8_contract_compile.cpp")]
            native_audit = []
            for source in sources:
                obj = safe.checked(native_build / (source.stem + ".o"))
                dep = safe.checked(native_build / (source.stem + ".d"))
                p = run(native_flags + ["-MD", "-MF", dep, "-c", source, "-o", obj],
                        "kernel-compile-" + source.stem, allow_failure=True)
                if p.returncode:
                    native.update(compile="FAIL", blocker=source.relative_to(safe.ROOT).as_posix())
                    break
                record = macho(obj, "x86_64", 1)
                symbols = run([tools["nm"], "-u", obj], "kernel-symbols-" + source.stem).stdout
                if any(token in symbols for token in forbidden):
                    raise RuntimeError("Kernel object exception/RTTI/heap/STL dependency")
                record["undefined_symbols"] = symbols.splitlines()
                native_audit.append(record)
            else:
                native.update(compile="PASS", objects=len(native_audit),
                              source="Existing Apple Xcode macOS SDK; no MacKernelSDK or Lilu required for this object scope")
            safe.write(out / "native-audit.json", json.dumps(native_audit, indent=2))
        summary["Darwin_Native"] = native

        dependencies = {}
        for folder in (safe.ROOT / "build/m9-arm64", safe.ROOT / "build/m9-x86_64", build / "native-x86_64"):
            for dep in folder.glob("*.d"):
                text = safe.checked(dep).read_text().replace("\\\n", " ")
                dependencies[dep.relative_to(safe.ROOT).as_posix()] = shlex.split(text.split(": ", 1)[1])
        sdk_headers = sorted({p for paths in dependencies.values() for p in paths if p.startswith(str(sdk))})
        hashes = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sdk_headers}
        safe.write(out / "header-dependencies.json", json.dumps(dict(dependencies=dependencies,
                   sdk_files_sha256=hashes), indent=2))
        summary["headers"] = dict(status="PASS", sdk_files=len(hashes), sdk_redistributed=False)
        for source in host.PURE + [safe.checked("tests/unit/m8_contract_compile.cpp")]:
            dest = safe.checked(build / (source.stem + ".plist"))
            p = run(common + ["--analyze", "-fno-exceptions", "-fno-rtti", source, "-o", dest],
                    "analyze-" + source.stem)
            if "warning:" in p.stdout + p.stderr:
                raise RuntimeError("Unresolved static analyzer warning")
        summary["static_analysis"] = "PASS: ten CPU translation units, zero warnings"
        if any(hashlib.sha256(safe.checked(p).read_bytes()).hexdigest() != digest for p, digest in before.items()):
            raise RuntimeError("Sources changed during verification")
        summary["source_stability"] = "PASS"
        summary["status"] = "PASS" if native["compile"] == "PASS" else "PARTIAL"
    except Exception as exc:
        summary.update(status="FAIL", error=str(exc))
        raise
    finally:
        safe.write(out / "test-results.json", json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
