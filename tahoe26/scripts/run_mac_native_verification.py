#!/usr/bin/env python3
"""PROJECT TAHOE26 — Apple Mac Native Verification Entry (M6 / M9-Mac).

Run this script on the user's real Apple Mac inside a clean clone of
`Hackintosh-Navi44-Lab` (branch `tahoe26-dev`).

Safety guarantees:
- Read-only inspection of Xcode / Apple Clang / SDK versions.
- Compiles ONLY the CPU-only Core and Darwin Native static adapter objects
  (`arm64` host test + `x86_64` Darwin target object check).
- NEVER installs, signs, or loads any Kext (`kextload`/`kmutil`), never modifies
  macOS SIP/AMFI, and never accesses GPU hardware.
"""
from pathlib import Path
import json
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "development" / "AMDRadeonRDNA4-Navi44" / "src"
CORE = ROOT / "development" / "AMDRadeonRDNA4-Navi44" / "core"
PLAT = ROOT / "development" / "AMDRadeonRDNA4-Navi44" / "platform"


def run_cmd(argv, cwd=ROOT, timeout=60):
    t0 = time.monotonic()
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return {
        "argv": [str(x) for x in argv],
        "exit": proc.returncode,
        "seconds": round(time.monotonic() - t0, 3),
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def main() -> int:
    if sys.platform != "darwin":
        print("SKIP: run_mac_native_verification.py must be executed on a real Apple Mac (sys.platform == 'darwin').")
        print("Current platform:", sys.platform)
        return 0

    out_dir = ROOT / "tahoe26" / "tests" / "native"
    build_dir = ROOT / "build" / "mac-native"
    out_dir.mkdir(parents=True, exist_ok=True)
    build_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version,
        "steps": [],
        "status": "RUNNING",
        "kext_load": "NOT_RUN_BY_DESIGN",
    }

    try:
        clang_info = run_cmd(["xcrun", "--find", "clang++"])
        report["steps"].append({"step": "find_clang", **clang_info})
        if clang_info["exit"] != 0:
            raise RuntimeError("xcrun --find clang++ failed")
        clang_path = clang_info["stdout"].splitlines()[0].strip()

        ver_info = run_cmd([clang_path, "--version"])
        report["steps"].append({"step": "clang_version", **ver_info})

        sdk_info = run_cmd(["xcrun", "--show-sdk-path"])
        report["steps"].append({"step": "sdk_path", **sdk_info})

        # Step 1: Run portable Host tests natively on Mac (arm64 or x86_64)
        host_test = run_cmd(
            [sys.executable, "-I", "-B", "-X", "utf8", str(ROOT / "run_host_tests.py"), "--compiler", clang_path, "--stage", "m9-host"],
            timeout=120,
        )
        report["steps"].append({"step": "portable_host_tests", **host_test})
        if host_test["exit"] != 0:
            raise RuntimeError("run_host_tests.py failed on macOS")

        # Step 2: Compile Core translation units explicitly for x86_64-apple-macos11.0 Mach-O object verification
        pure_sources = [
            SRC / "codeobj.cpp",
            SRC / "ipdiscovery.cpp",
            CORE / "validation.cpp",
            CORE / "device_info.cpp",
            SRC / "edid.cpp",
            SRC / "atombios.cpp",
            CORE / "display.cpp",
            CORE / "integrity.cpp",
            CORE / "query_candidate.cpp",
        ]
        macho_objects = []
        for src_file in pure_sources:
            obj_file = build_dir / (src_file.stem + ".x86_64.o")
            cmd = [
                clang_path,
                "-target",
                "x86_64-apple-macos11.0",
                "-std=c++17",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-fno-exceptions",
                "-fno-rtti",
                "-ffreestanding",
                "-Wframe-larger-than=4096",
                "-O1",
                "-g",
                "-I" + str(SRC),
                "-c",
                str(src_file),
                "-o",
                str(obj_file),
            ]
            res = run_cmd(cmd)
            report["steps"].append({"step": f"macho_x86_64_{src_file.stem}", **res})
            if res["exit"] != 0:
                raise RuntimeError(f"Mach-O x86_64 compile failed for {src_file.name}")
            macho_objects.append(str(obj_file))

        nm_res = run_cmd(["xcrun", "nm", "-u", *macho_objects])
        report["steps"].append({"step": "macho_undefined_symbols", **nm_res})
        report["status"] = "VERIFIED_NATIVE_BUILD"
    except Exception as exc:
        report["status"] = "FAILED"
        report["error"] = str(exc)
        (out_dir / "mac-native-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        raise

    (out_dir / "mac-native-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
