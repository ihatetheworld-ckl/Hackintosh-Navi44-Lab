"""Portable CPU-only Host build; no SDK downloads, driver targets or GPU backend.

Requires an existing trusted C++17 compiler and Python 3.11+. Mac execution
remains NOT RUN until independently validated with real Apple Clang.
"""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import time

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
    parser.add_argument("--stage", default="host", choices=["host", "m85-host", "m9-host"])
    args = parser.parse_args()
    compiler = Path(args.compiler)
    if not compiler.is_absolute() or not compiler.is_file():
        raise SystemExit("Supply an existing compiler absolute path; no auto-install")
    build = safe.mkdir("build/" + args.stage)
    out = safe.mkdir("reports/" + args.stage)
    temp = safe.mkdir("tmp/" + args.stage)
    env = os.environ.copy()
    env.update(TMP=str(temp), TEMP=str(temp), TMPDIR=str(temp),
               CLANG_MODULE_CACHE_PATH=str(safe.mkdir(build / "cache")),
               PYTHONDONTWRITEBYTECODE="1")
    records = []
    base = [str(compiler), "-std=c++17", "-Wall", "-Wextra", "-Werror",
            "-UNDEBUG", "-O1", "-g", "-I" + str(SRC)]

    def run(command, name):
        command = [str(x) for x in command]
        if "-o" in command:
            safe.checked(command[command.index("-o") + 1])
        began = time.monotonic()
        try:
            result = subprocess.run(command, cwd=safe.ROOT, env=env,
                                    capture_output=True, text=True,
                                    encoding="utf-8", timeout=60)
        except subprocess.TimeoutExpired:
            records.append({"name": name, "argv": command, "exit": None,
                            "status": "TIMEOUT", "seconds": round(time.monotonic()-began, 3)})
            raise
        records.append({"name": name, "argv": command, "exit": result.returncode,
                        "seconds": round(time.monotonic()-began, 3)})
        safe.write(out / (name + ".log"), result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(name + " failed; see project report")
        return result.stdout + result.stderr

    summary = {"status": "RUNNING", "kind": "CPU-only Host", "platform": sys.platform,
               "Darwin_Native": "NOT RUN", "Kext": "NOT RUN", "GPU": "NOT RUN",
               "differential": "NOT RUN by portable entry",
               "sanitizer": "NOT RUN by portable entry"}
    safe.write(out / "results.json", json.dumps(summary, indent=2))
    try:
        summary["compiler"] = run([compiler, "--version"], "compiler-version").strip()
        for test in PYTESTS:
            run([sys.executable, "-I", "-B", "-X", "utf8",
                 safe.checked("tests/" + test)], "python-" + Path(test).stem)
        objects = []
        for source in PURE:
            safe.checked(source)
            obj = safe.checked(build / (source.stem + ".o"))
            run(base + ["-fno-exceptions", "-fno-rtti", "-ffreestanding",
                        "-Wframe-larger-than=4096", "-c", source, "-o", obj],
                "core-" + source.stem)
            objects.append(obj)
        offline = safe.checked(build / "offlinevalidation.o")
        run(base + ["-c", SRC / "offlinevalidation.cpp", "-o", offline], "host-adapter")
        extra = ".exe" if os.name == "nt" else ""
        unit_counts = {}
        for name in TESTS:
            executable = safe.checked(build / (name + extra))
            linkage = ["-static"] if os.name == "nt" else []
            deps = objects + ([offline] if name in ("m65_unit", "m7_unit") else [])
            run(base + linkage + [safe.checked("tests/unit/" + name + ".cpp"),
                                   *deps, "-o", executable], "build-" + name)
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
        summary.update(status="PASS", cpp_unit=unit_counts, python_files=PYTESTS,
                       kernel_friendly_host_compile="PASS")
    except Exception as exc:
        summary.update(status="FAIL", error=str(exc))
        raise
    finally:
        safe.write(out / "commands.json", json.dumps(records, ensure_ascii=False, indent=2))
        safe.write(out / "results.json", json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
