"""Portable CPU-only Host build; no SDK downloads, driver targets or GPU backend.

Requires an existing trusted C++17 compiler and Python 3.11+.
Architecture, compile/link and CPU execution results are recorded separately.
"""
from pathlib import Path
import argparse
import json
import os
import platform
import re
import subprocess
import sys
import time

if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11+ required; select an existing interpreter, no auto-install")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m7_safety as safe

SRC = safe.ROOT / "development/AMDRadeonRDNA4-Navi44/src"
CORE = SRC.parent / "core"
PURE = [
    SRC / "codeobj.cpp", SRC / "ipdiscovery.cpp",
    CORE / "validation.cpp", CORE / "device_info.cpp",
    SRC / "edid.cpp", SRC / "atombios.cpp",
    CORE / "display.cpp", CORE / "integrity.cpp", CORE / "query_candidate.cpp",
]
TESTS = ["m65_unit", "m7_unit", "m8_unit", "m8_fuzz"]
PYTESTS = ["test_offline.py", "test_m65.py", "test_m7.py", "test_m8.py"]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", required=True, help="Existing trusted clang++ absolute path")
    parser.add_argument("--stage", default="host", choices=["host", "m85-host", "m9-host",
                        "m9-arm64", "m9-x86_64", "m9-sanitized"])
    parser.add_argument("--arch", choices=["arm64", "x86_64"], help="macOS target architecture")
    parser.add_argument("--sdk", help="Existing macOS SDK absolute path; default: xcrun macosx SDK")
    parser.add_argument("--compile-only", action="store_true", help="Compile and link; never execute target binaries")
    parser.add_argument("--skip-python", action="store_true", help="Do not duplicate architecture-independent Python tests")
    parser.add_argument("--sanitize", action="store_true", help="Instrument all CPU objects and tests with ASan/UBSan")
    args = parser.parse_args()
    compiler = Path(args.compiler)
    if not compiler.is_absolute() or not compiler.is_file():
        raise SystemExit("Supply an existing compiler absolute path; no auto-install")
    if (args.arch or args.sdk) and sys.platform != "darwin":
        raise SystemExit("--arch/--sdk require macOS; Windows defaults are unchanged")
    build = safe.mkdir("build/" + args.stage)
    out = safe.mkdir("reports/" + args.stage)
    temp = safe.mkdir("tmp/" + args.stage)
    env = os.environ.copy()
    env.update(TMP=str(temp), TEMP=str(temp), TMPDIR=str(temp),
               CLANG_MODULE_CACHE_PATH=str(safe.mkdir(build / "cache")),
               PYTHONDONTWRITEBYTECODE="1")
    if args.sanitize:
        env.update(ASAN_OPTIONS="halt_on_error=1:detect_leaks=0:abort_on_error=0",
                   UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
    records = []
    def run(command, name, stdout_only=False):
        command = [str(x) for x in command]
        if "-o" in command:
            safe.checked(command[command.index("-o") + 1])
        began = time.monotonic()
        try:
            result = subprocess.run(command, cwd=safe.ROOT, env=env,
                                    capture_output=True, text=True,
                                    encoding="utf-8", timeout=60)
        except subprocess.TimeoutExpired as exc:
            records.append({"name": name, "argv": command, "exit": None,
                            "status": "TIMEOUT", "seconds": round(time.monotonic()-began, 3)})
            safe.write(out / (name + ".log"), "TIMEOUT\n" +
                       (exc.stdout or b"").decode("utf-8", errors="replace") +
                       (exc.stderr or b"").decode("utf-8", errors="replace"))
            raise
        records.append({"name": name, "argv": command, "exit": result.returncode,
                        "seconds": round(time.monotonic()-began, 3)})
        safe.write(out / (name + ".log"), result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(name + " failed; see project report")
        return result.stdout if stdout_only else result.stdout + result.stderr

    summary = {"status": "RUNNING", "kind": "CPU-only Host", "platform": sys.platform,
               "host_arch": platform.machine(), "target_arch": args.arch or platform.machine(),
               "compile": "NOT RUN", "link": "NOT RUN", "runtime": "NOT RUN",
               "Darwin_Native": "NOT RUN", "Kext": "NOT RUN", "GPU": "NOT RUN",
               "differential": "NOT RUN by portable entry",
               "sanitizer": "ASan/UBSan requested" if args.sanitize else "NOT RUN by portable entry",
               "python": "NOT RUN" if args.skip_python else "PENDING"}
    safe.write(out / "results.json", json.dumps(summary, indent=2))
    try:
        summary["compiler"] = run([compiler, "--version"], "compiler-version").strip()
        base = [str(compiler), "-std=c++17", "-Wall", "-Wextra", "-Werror",
                "-UNDEBUG", "-O1", "-g", "-I" + str(SRC)]
        if sys.platform == "darwin":
            sdk = Path(args.sdk or run(["xcrun", "--sdk", "macosx", "--show-sdk-path"],
                                      "sdk-path", stdout_only=True).strip())
            if not sdk.is_absolute() or not sdk.is_dir():
                raise RuntimeError("An existing genuine macOS SDK path is required")
            base += ["-isysroot", str(sdk), "-arch", args.arch or platform.machine(),
                     "-mmacosx-version-min=13.0"]
            summary["sdk"] = str(sdk)
        if args.sanitize:
            base += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
        python_counts = {}
        for test in ([] if args.skip_python else PYTESTS):
            log = run([sys.executable, "-I", "-B", "-X", "utf8",
                 safe.checked("tests/" + test)], "python-" + Path(test).stem)
            total = re.search(r"Ran (\d+) tests?", log)
            if not total:
                raise RuntimeError("Missing Python execution summary")
            skip = re.search(r"OK \(skipped=(\d+)\)", log)
            count, skipped = int(total[1]), int(skip[1]) if skip else 0
            python_counts[test] = {"PASS": count - skipped, "SKIP": skipped, "FAIL": 0}
        objects = []
        for source in PURE:
            safe.checked(source)
            obj = safe.checked(build / (source.stem + ".o"))
            run(base + ["-fno-exceptions", "-fno-rtti", "-ffreestanding",
                        "-Wframe-larger-than=4096", "-MD", "-MF", build / (source.stem + ".d"),
                        "-c", source, "-o", obj],
                "core-" + source.stem)
            objects.append(obj)
        offline = safe.checked(build / "offlinevalidation.o")
        run(base + ["-c", SRC / "offlinevalidation.cpp", "-o", offline], "host-adapter")
        extra = ".exe" if os.name == "nt" else ""
        unit_counts = {}
        summary["compile"] = "PASS"
        for name in TESTS:
            executable = safe.checked(build / (name + extra))
            linkage = ["-static"] if os.name == "nt" else []
            deps = objects + ([offline] if name in ("m65_unit", "m7_unit") else [])
            run(base + linkage + [safe.checked("tests/unit/" + name + ".cpp"),
                                   *deps, "-o", executable], "build-" + name)
            if args.compile_only:
                continue
            log = run([executable], "run-" + name)
            if name.endswith("unit"):
                unit_counts[name] = sum(row.startswith("PASS ") for row in log.splitlines())
                if unit_counts[name] == 0:
                    raise RuntimeError("Unit test returned no successful assertions")
            else:
                summary["bounded_mutation_output"] = log.strip()
        run(base + ["-fno-exceptions", "-fno-rtti", "-ffreestanding",
                    "-c", safe.checked("tests/unit/m8_contract_compile.cpp"),
                    "-o", safe.checked(build / "contract.o")], "platform-contract")
        summary.update(status="PASS", link="PASS", runtime="NOT RUN" if args.compile_only else "PASS",
                       cpp_unit=unit_counts, python=python_counts if not args.skip_python else "NOT RUN",
                       python_files=[] if args.skip_python else PYTESTS,
                       kernel_friendly_host_compile="PASS")
        if args.sanitize:
            summary["sanitizer"] = "NOT RUN" if args.compile_only else "PASS; leak detection NOT VERIFIED"
    except Exception as exc:
        summary.update(status="FAIL", error=str(exc))
        raise
    finally:
        safe.write(out / "commands.json", json.dumps(records, ensure_ascii=False, indent=2))
        safe.write(out / "results.json", json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
