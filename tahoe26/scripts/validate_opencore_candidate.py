"""PROJECT TAHOE26 — Offline OpenCore 1.0.8 Candidate Validator (Dry-Run Only).

Validates plist syntax, schema keys, Alder Lake CPUID emulation, Maxsun B760M D5
DeviceProperties PCI paths, WhateverGreen conflict isolation, and Windows SSD
protection flags without touching any system disk or EFI partition.
"""
from pathlib import Path
import hashlib
import json
import plistlib
import sys

ROOT = Path(__file__).resolve().parents[2]
OC_DIR = ROOT / "tahoe26" / "opencore"
CONFIG_PATH = OC_DIR / "EFI" / "OC" / "config.plist"
UTBMAP_PATH = OC_DIR / "EFI" / "OC" / "Kexts" / "UTBMap.kext" / "Contents" / "Info.plist"
ACPI_DIR = OC_DIR / "acpi"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    checks = []

    def check(name: str, cond: bool, detail: str = ""):
        checks.append({"name": name, "status": "PASS" if cond else "FAIL", "detail": detail})

    check("config_exists", CONFIG_PATH.is_file(), str(CONFIG_PATH.relative_to(ROOT)))
    check("utbmap_exists", UTBMAP_PATH.is_file(), str(UTBMAP_PATH.relative_to(ROOT)))

    with CONFIG_PATH.open("rb") as f:
        cfg = plistlib.load(f)
    with UTBMAP_PATH.open("rb") as f:
        utb = plistlib.load(f)

    required_top = {"ACPI", "Booter", "DeviceProperties", "Kernel", "Misc", "NVRAM", "PlatformInfo", "UEFI"}
    check("top_level_sections", set(cfg.keys()) == required_top, ",".join(sorted(cfg.keys())))

    # Check ACPI DSL counterparts
    acpi_entries = cfg["ACPI"]["Add"]
    dsl_map = {
        "SSDT-PLUG-ALT.aml": "SSDT-PLUG-ALT.dsl",
        "SSDT-EC-USBX.aml": "SSDT-EC-USBX.dsl",
        "SSDT-RTCAWAC.aml": "SSDT-RTCAWAC.dsl",
        "SSDT-NVME-PROTECT.aml": "SSDT-NVME-PROTECT.dsl",
    }
    all_dsl_ok = True
    for entry in acpi_entries:
        dsl_name = dsl_map.get(entry["Path"], "")
        if not dsl_name or not (ACPI_DIR / dsl_name).is_file():
            all_dsl_ok = False
    check("acpi_dsl_sources_present", all_dsl_ok, f"{len(acpi_entries)} SSDT templates audited")

    # Alder Lake CPUID emulation check (0x0A0655 Comet Lake)
    emulate = cfg["Kernel"]["Emulate"]
    cpuid_data = emulate["Cpuid1Data"]
    cpuid_mask = emulate["Cpuid1Mask"]
    check(
        "alder_lake_cpuid_spoof",
        cpuid_data[:4] == b"\x55\x06\x0a\x00" and cpuid_mask[:4] == b"\xff\xff\xff\xff",
        f"Cpuid1Data={cpuid_data[:4].hex()}",
    )

    # Kernel Quirks for Alder Lake + Windows SMBIOS isolation
    kquirks = cfg["Kernel"]["Quirks"]
    check(
        "kernel_quirks_alder_lake",
        kquirks.get("ProvideCurrentCpuInfo") is True
        and kquirks.get("AppleXcpmCfgLock") is True
        and kquirks.get("CustomSMBIOSGuid") is True
        and kquirks.get("XhciPortLimit") is False,
        "ProvideCurrentCpuInfo=True, CustomSMBIOSGuid=True, XhciPortLimit=False",
    )

    # PlatformInfo SMBIOS isolation check
    pinfo = cfg["PlatformInfo"]
    check(
        "smbios_macpro71_isolated",
        pinfo["Generic"]["SystemProductName"] == "MacPro7,1"
        and pinfo["UpdateSMBIOSMode"] == "Create"
        and "PLACEHOLDER" in pinfo["Generic"]["SystemSerialNumber"],
        "MacPro7,1 + UpdateSMBIOSMode=Create + No leaked serials",
    )

    # WhateverGreen and experimental GPU kext safety gate check
    kexts = {k["BundlePath"]: k for k in cfg["Kernel"]["Add"]}
    check(
        "whatevergreen_conflict_disabled",
        "WhateverGreen.kext" in kexts and kexts["WhateverGreen.kext"]["Enabled"] is False,
        "WhateverGreen.kext Enabled=False (avoids RDNA4 conflict)",
    )
    check(
        "experimental_rdna4_gated",
        "AMDRadeonRDNA4.kext" in kexts and kexts["AMDRadeonRDNA4.kext"]["Enabled"] is False,
        "AMDRadeonRDNA4.kext Enabled=False until Gate D",
    )
    check(
        "core_kexts_enabled",
        kexts["Lilu.kext"]["Enabled"] is True
        and kexts["VirtualSMC.kext"]["Enabled"] is True
        and kexts["LucyRTL8125Ethernet.kext"]["Enabled"] is True
        and kexts["CpuTopologyRebuild.kext"]["Enabled"] is True,
        "Lilu, VirtualSMC, LucyRTL8125Ethernet, CpuTopologyRebuild enabled",
    )

    # Windows Boot Manager protection check
    check(
        "windows_boot_var_routing",
        cfg["UEFI"]["Quirks"]["RequestBootVarRouting"] is True
        and cfg["Misc"]["Boot"]["LauncherOption"] == "Full",
        "RequestBootVarRouting=True, LauncherOption=Full",
    )

    # Mandatory non-physical Windows NVMe isolation check (PciRoot(0x0)/Pci(0x6,0x0)/Pci(0x0,0x0))
    win_nvme_dp = cfg["DeviceProperties"]["Add"].get("PciRoot(0x0)/Pci(0x6,0x0)/Pci(0x0,0x0)", {})
    nvme_ssdt = [x for x in cfg["ACPI"]["Add"] if x["Path"] == "SSDT-NVME-PROTECT.aml"]
    check(
        "windows_nvme_software_isolated",
        win_nvme_dp.get("class-code") == b"\xff\xff\xff\xff"
        and win_nvme_dp.get("IOName") == "#disabled-nvme"
        and len(nvme_ssdt) == 1
        and nvme_ssdt[0]["Enabled"] is True,
        "Pci(0x6,0x0)/Pci(0x0,0x0) class-code=FFFFFFFF + SSDT-NVME-PROTECT Enabled=True",
    )

    # UTBMap check for Maxsun B760M D5 XHCI (8086:7a60) and Bluetooth HS14
    personalities = utb.get("IOKitPersonalities", {}).get("Maxsun_B760M_D5_XHCI", {})
    ports = personalities.get("IOProviderMergeProperties", {}).get("ports", {})
    check(
        "utbmap_b760_ports_valid",
        personalities.get("IOPCIMatch") == "0x7a608086"
        and len(ports) == 15
        and "HS14" in ports
        and ports["HS14"]["UsbConnector"] == 255,
        f"IOPCIMatch=0x7a608086, {len(ports)} ports (<=15 limit), HS14 internal BT mapped",
    )

    failed = [c for c in checks if c["status"] != "PASS"]
    report = {
        "validator": "validate_opencore_candidate.py",
        "mode": "DRY_RUN_READ_ONLY",
        "status": "PASS" if not failed else "FAIL",
        "total_checks": len(checks),
        "passed": len(checks) - len(failed),
        "failed": len(failed),
        "artifacts": {
            "config.plist": sha256_file(CONFIG_PATH),
            "UTBMap_Info.plist": sha256_file(UTBMAP_PATH),
        },
        "checks": checks,
    }
    out_dir = ROOT / "tahoe26" / "tests" / "host"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "opencore-validation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
