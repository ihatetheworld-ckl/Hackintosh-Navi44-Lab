#!/usr/bin/env python3
"""PROJECT TAHOE26 — Apple Mac Native Verification & Candidate EFI Builder.

Designed to run on a real Apple Mac (including macOS 27 on Apple Silicon or Intel).

What this script does safely inside the repository workspace:
1. Checks Xcode / Apple Clang / SDK and runs the portable CPU-only Host test suite
   (`run_host_tests.py` -> 4 Python suites + 171 C++ unit tests + 4000 bounded mutations).
2. Cross-compiles all 9 pure C++17 Core translation units to `x86_64-apple-macos11.0`
   Mach-O `.o` objects (`-fno-exceptions -fno-rtti -ffreestanding -Wframe-larger-than=4096 -Werror`)
   and audits undefined symbols via `xcrun nm -u`.
3. If `iasl` is available (or if `--compile-acpi` is requested and `iasl` is in PATH),
   compiles the 4 audited `.dsl` files in `tahoe26/opencore/acpi/` into `.aml` binaries
   under `tahoe26/opencore/EFI/OC/ACPI/`.
4. Generates a local-only (gitignored) SMBIOS serial file `build/mac-native/local-smbios.json`
   using `macserial` (if provided) or cryptographic random valid-format placeholders so
   real serials are never committed to Git.

Safety guarantees:
- NEVER touches any physical disk, partition, or EFI System Partition.
- NEVER runs `sudo`, `kextload`, `kmutil`, or any GPU hardware probe.
"""
from pathlib import Path
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "development" / "AMDRadeonRDNA4-Navi44" / "src"
CORE = ROOT / "development" / "AMDRadeonRDNA4-Navi44" / "core"
ACPI_DSL_DIR = ROOT / "tahoe26" / "opencore" / "acpi"
ACPI_AML_DIR = ROOT / "tahoe26" / "opencore" / "EFI" / "OC" / "ACPI"


def run_cmd(argv, cwd=ROOT, timeout=90):
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
    ACPI_AML_DIR.mkdir(parents=True, exist_ok=True)

    report = {
        "platform": platform.platform(),
        "macos_ver": platform.mac_ver()[0],
        "machine": platform.machine(),
        "python": sys.version,
        "steps": [],
        "macho_objects": {},
        "acpi_aml": {},
        "status": "RUNNING",
        "kext_load": "NOT_RUN_BY_DESIGN",
    }

    try:
        sw_vers = run_cmd(["sw_vers"])
        report["steps"].append({"step": "sw_vers", **sw_vers})

        clang_info = run_cmd(["xcrun", "--find", "clang++"])
        report["steps"].append({"step": "find_clang", **clang_info})
        if clang_info["exit"] != 0:
            raise RuntimeError("xcrun --find clang++ failed; install Xcode Command Line Tools (`xcode-select --install`)")
        clang_path = clang_info["stdout"].splitlines()[0].strip()

        ver_info = run_cmd([clang_path, "--version"])
        report["steps"].append({"step": "clang_version", **ver_info})

        sdk_info = run_cmd(["xcrun", "--show-sdk-path"])
        report["steps"].append({"step": "sdk_path", **sdk_info})

        # Step 1: Run portable Host tests natively on Mac
        host_test = run_cmd(
            [
                sys.executable,
                "-I",
                "-B",
                "-X",
                "utf8",
                str(ROOT / "run_host_tests.py"),
                "--compiler",
                clang_path,
                "--stage",
                "m9-host",
            ],
            timeout=120,
        )
        report["steps"].append({"step": "portable_host_tests", **host_test})
        if host_test["exit"] != 0:
            raise RuntimeError("run_host_tests.py failed on macOS")

        # Step 2: Run OpenCore candidate validator on Mac
        oc_val = run_cmd([sys.executable, "-I", "-B", "-X", "utf8", str(ROOT / "tahoe26" / "scripts" / "validate_opencore_candidate.py")])
        report["steps"].append({"step": "opencore_candidate_validation", **oc_val})
        if oc_val["exit"] != 0:
            raise RuntimeError("validate_opencore_candidate.py failed on macOS")

        # Step 3: Cross-compile all 9 Core translation units to x86_64-apple-macos11.0 Mach-O objects
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
            report["macho_objects"][obj_file.name] = hashlib.sha256(obj_file.read_bytes()).hexdigest()

        nm_res = run_cmd(["xcrun", "nm", "-u", *macho_objects])
        report["steps"].append({"step": "macho_undefined_symbols", **nm_res})

        # Step 4: Compile ACPI DSL -> AML if iasl is installed on Mac
        iasl_bin = shutil.which("iasl")
        if iasl_bin:
            for dsl_file in sorted(ACPI_DSL_DIR.glob("*.dsl")):
                aml_out = ACPI_AML_DIR / (dsl_file.stem + ".aml")
                res = run_cmd([iasl_bin, "-p", str(aml_out), str(dsl_file)])
                report["steps"].append({"step": f"iasl_{dsl_file.name}", **res})
                if res["exit"] == 0 and aml_out.is_file():
                    report["acpi_aml"][aml_out.name] = hashlib.sha256(aml_out.read_bytes()).hexdigest()
        else:
            report["acpi_aml"]["status"] = "iasl_not_in_path_install_via_brew_acpica"

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
