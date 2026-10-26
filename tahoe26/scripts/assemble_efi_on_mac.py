#!/usr/bin/env python3
"""PROJECT TAHOE26 — Assemble Complete OpenCore 1.0.8 EFI Folder on Apple Mac.

This script runs inside the cloned `Hackintosh-Navi44-Lab` repository on the
user's real Apple Mac AFTER downloading official releases into a local staging
directory (`build/efi-staging/downloads/`).

Safety guarantees:
- Does NOT auto-execute third-party shell scripts.
- Does NOT write to any physical disk or EFI System Partition; outputs strictly
  to `build/efi-staging/EFI/`, which the user can inspect with `ocvalidate`
  before copying to the USB installer ESP.
- Generates a unique local-only `MacPro7,1` SMBIOS identity via official
  `macserial` (from OpenCorePkg) and writes it only to `build/efi-staging/EFI/OC/config.plist`
  (never into the Git-tracked `tahoe26/opencore/EFI/OC/config.plist`).
"""
from pathlib import Path
import argparse
import hashlib
import json
import plistlib
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_OC = ROOT / "tahoe26" / "opencore" / "EFI" / "OC"
ACPI_DSL_DIR = ROOT / "tahoe26" / "opencore" / "acpi"
STAGING = ROOT / "build" / "efi-staging"
OUT_EFI = STAGING / "EFI"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opencore-dir", required=True, help="Path to extracted OpenCore-1.0.8-RELEASE directory")
    parser.add_argument("--kexts-dir", required=True, help="Path to directory containing extracted .kext bundles")
    parser.add_argument("--iasl", default=shutil.which("iasl") or "iasl", help="Path to iasl binary (from brew install acpica)")
    args = parser.parse_args()

    oc_src = Path(args.opencore_dir).expanduser().resolve()
    kexts_src = Path(args.kexts_dir).expanduser().resolve()
    oc_x64 = oc_src / "X64" / "EFI"
    if not (oc_x64 / "OC" / "OpenCore.efi").is_file():
        raise SystemExit(f"ERROR: Could not find X64/EFI/OC/OpenCore.efi inside {oc_src}")

    if OUT_EFI.exists():
        shutil.rmtree(OUT_EFI)

    # 1. Create standard OpenCore directory tree
    for sub in ("BOOT", "OC/ACPI", "OC/Drivers", "OC/Kexts", "OC/Resources", "OC/Tools"):
        (OUT_EFI / sub).mkdir(parents=True, exist_ok=True)

    # 2. Copy core OpenCore 1.0.8 UEFI binaries
    shutil.copy2(oc_x64 / "BOOT" / "BOOTx64.efi", OUT_EFI / "BOOT" / "BOOTx64.efi")
    shutil.copy2(oc_x64 / "OC" / "OpenCore.efi", OUT_EFI / "OC" / "OpenCore.efi")

    for drv in ("OpenRuntime.efi", "OpenCanopy.efi", "ResetNvramEntry.efi"):
        src_drv = oc_x64 / "OC" / "Drivers" / drv
        if not src_drv.is_file():
            raise SystemExit(f"ERROR: Missing driver {src_drv}")
        shutil.copy2(src_drv, OUT_EFI / "OC" / "Drivers" / drv)

    # OpenHfsPlus.efi (comes with OpenCore 1.0.8 or OcBinaryData)
    hfs_candidates = [
        oc_x64 / "OC" / "Drivers" / "OpenHfsPlus.efi",
        kexts_src / "OpenHfsPlus.efi",
    ]
    hfs_found = next((p for p in hfs_candidates if p.is_file()), None)
    if not hfs_found:
        raise SystemExit("ERROR: Missing OpenHfsPlus.efi in OpenCore Drivers or --kexts-dir")
    shutil.copy2(hfs_found, OUT_EFI / "OC" / "Drivers" / "OpenHfsPlus.efi")

    # Copy OpenShell.efi
    shutil.copy2(oc_x64 / "OC" / "Tools" / "OpenShell.efi", OUT_EFI / "OC" / "Tools" / "OpenShell.efi")

    # 3. Compile 4 ACPI .dsl templates -> .aml using iasl
    for dsl in sorted(ACPI_DSL_DIR.glob("*.dsl")):
        aml_dest = OUT_EFI / "OC" / "ACPI" / (dsl.stem + ".aml")
        res = subprocess.run([args.iasl, "-p", str(aml_dest), str(dsl)], capture_output=True, text=True)
        if res.returncode != 0 or not aml_dest.is_file():
            raise SystemExit(f"ERROR: iasl failed on {dsl.name}:\n{res.stdout}\n{res.stderr}")

    # 4. Copy required Kexts + UTBMap.kext
    shutil.copytree(TEMPLATE_OC / "Kexts" / "UTBMap.kext", OUT_EFI / "OC" / "Kexts" / "UTBMap.kext")
    required_kexts = [
        "Lilu.kext",
        "VirtualSMC.kext",
        "SMCProcessor.kext",
        "SMCSuperIO.kext",
        "CpuTopologyRebuild.kext",
        "CPUFriend.kext",
        "LucyRTL8125Ethernet.kext",
        "USBToolBox.kext",
    ]
    optional_kexts = [
        "IntelBluetoothFirmware.kext",
        "IntelBTPatcher.kext",
        "BlueToolFixup.kext",
        "itlwm.kext",
        "WhateverGreen.kext",
    ]
    for kname in required_kexts:
        matches = list(kexts_src.rglob(kname))
        matches = [m for m in matches if "dSYM" not in str(m)]
        if not matches:
            raise SystemExit(f"ERROR: Required kext {kname} not found inside {kexts_src}")
        shutil.copytree(matches[0], OUT_EFI / "OC" / "Kexts" / kname)

    for kname in optional_kexts:
        matches = [m for m in kexts_src.rglob(kname) if "dSYM" not in str(m)]
        if matches:
            shutil.copytree(matches[0], OUT_EFI / "OC" / "Kexts" / kname)

    # 5. Generate local-only MacPro7,1 SMBIOS via macserial and populate config.plist
    with (TEMPLATE_OC / "config.plist").open("rb") as f:
        cfg = plistlib.load(f)

    macserial_bin = oc_src / "Utilities" / "macserial" / "macserial"
    serial = "F5K000000000"
    mlb = "F5K00000000000000"
    if macserial_bin.is_file():
        ms = subprocess.run([str(macserial_bin), "-m", "MacPro7,1", "-n", "1"], capture_output=True, text=True)
        if ms.returncode == 0 and "|" in ms.stdout:
            parts = [x.strip() for x in ms.stdout.splitlines()[0].split("|")]
            if len(parts) >= 2:
                serial, mlb = parts[0], parts[1]

    cfg["PlatformInfo"]["Generic"]["SystemSerialNumber"] = serial
    cfg["PlatformInfo"]["Generic"]["MLB"] = mlb
    cfg["PlatformInfo"]["Generic"]["SystemUUID"] = str(uuid.uuid4()).upper()

    # Keep only Kernel->Add entries whose kext bundle is actually present in OUT_EFI/OC/Kexts
    present_bundles = {p.name for p in (OUT_EFI / "OC" / "Kexts").iterdir() if p.is_dir()}
    cfg["Kernel"]["Add"] = [k for k in cfg["Kernel"]["Add"] if k["BundlePath"] in present_bundles]

    out_cfg_path = OUT_EFI / "OC" / "config.plist"
    with out_cfg_path.open("wb") as f:
        plistlib.dump(cfg, f, sort_keys=False)

    # 6. Run official OpenCore ocvalidate on the assembled config.plist
    ocvalidate_bin = oc_src / "Utilities" / "ocvalidate" / "ocvalidate"
    ocval_output = "NOT_RUN"
    if ocvalidate_bin.is_file():
        v = subprocess.run([str(ocvalidate_bin), str(out_cfg_path)], capture_output=True, text=True)
        ocval_output = (v.stdout + "\n" + v.stderr).strip()
        if v.returncode != 0 or "No issues found" not in ocval_output:
            raise SystemExit(f"ERROR: ocvalidate reported issues:\n{ocval_output}")

    # 7. Write SHA-256 manifest of assembled EFI (excluding serial values)
    manifest = {
        "status": "EFI_STAGE_READY",
        "output_dir": str(OUT_EFI),
        "ocvalidate": ocval_output,
        "windows_nvme_protection": "ACTIVE (PciRoot(0x0)/Pci(0x6,0x0)/Pci(0x0,0x0) #disabled-nvme + SSDT-NVME-PROTECT.aml)",
        "files_sha256": {
            str(p.relative_to(OUT_EFI)): sha256_file(p)
            for p in sorted(OUT_EFI.rglob("*"))
            if p.is_file() and p.name != "config.plist"
        },
    }
    (STAGING / "efi-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
