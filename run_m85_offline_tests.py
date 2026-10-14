"""M8.5 migration validation: reviewed M8 CPU pipeline, isolated outputs.

No downloads, installation, driver build, hardware access, or remote operations.
Historical runner definitions and M6/M7/M8 reports are preserved unchanged.
"""
from pathlib import Path
import hashlib
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m7_safety as safe

EXPECTED = {
    "run_m8_offline_tests.py": "9933563b96a1e1b1d56ad803fd4230c27f6909d7d352464d23e5c83c6efd910c",
}

def main():
    for name, digest in EXPECTED.items():
        if hashlib.sha256(safe.checked(name).read_bytes()).hexdigest() != digest:
            raise SystemExit("Reviewed runner changed; review before executing: " + name)
    for name in ("tmp", "build/m85/validation", "reports/m85/validation"):
        safe.mkdir(name)
    # The inherited helper boundary and CPU-only source allowlist were audited.
    # Redirect every M8 result/build reference, including its M7 regression.
    text = safe.checked("run_m8_offline_tests.py").read_text(encoding="utf-8")
    text = text.replace("reports/m8", "reports/m85/validation")
    text = text.replace("build/m8", "build/m85/validation")
    safe.preflight([
        "tests/fixtures/m65-invalid-strtab.bin",
        "run_all_offline_tests.py", "run_m7_offline_tests.py",
        "tools/toolchains/llvm", "reports/m85/validation", "build/m85/validation",
    ])
    scope = {"__file__": str(safe.ROOT / "run_m8_offline_tests.py"),
             "__name__": "__main__"}
    exec(compile(text, "reviewed-M8-migration-validation", "exec"), scope)

if __name__ == "__main__":
    main()
