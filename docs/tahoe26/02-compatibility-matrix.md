# 02 — macOS 26 Tahoe 兼容性矩阵 (Compatibility Matrix)

详见 [compatibility-inventory.md](../../tahoe26/hardware/compatibility-inventory.md)。

| 模块 | 状态 | 适配策略 |
|---|---|---|
| CPU (`i5-12600KF`) | `VERIFIED_HOST_ONLY` | Comet Lake `0x0A0655` CPUID 仿冒 + `CpuTopologyRebuild.kext` + `ProvideCurrentCpuInfo=true` + `SSDT-PLUG-ALT` |
| 主板 (`MS-Terminator B760M D5`) | `VERIFIED_HOST_ONLY` | `SSDT-EC-USBX` + `SSDT-RTCAWAC` + `AppleXcpmCfgLock=true` |
| 目标盘 (`INTEL SSDPEKKF256G8L`) | `UPSTREAM_REPORTED` | macOS 原生 `IONVMeFamily` 直接支持 |
| 有线网络 (`RTL8125` `10EC:8125`) | `UPSTREAM_REPORTED` | `LucyRTL8125Ethernet.kext` `v1.2.2` |
| 蓝牙 (`8087:0026`) | `UPSTREAM_REPORTED` | `IntelBluetoothFirmware` + `IntelBTPatcher` + `BlueToolFixup` + `-ibtcompatbeta` |
| 无线网络 (`AX101` `8086:7A70`) | `UNVERIFIED` | 候选 `itlwm.kext` (HeliPort) 或 Tahoe 分支 `AirportItlwm`；需真机验证 CNVi `7A70` |
| 音频 (`USB Audio` / `ALC897`) | `UPSTREAM_REPORTED` (USB) / `BLOCKED` (ALC897 无降级 SIP 时) | Tahoe 移除了 `AppleHDA.kext`；优先使用本机已连接的 `Philips SPA3609 USB` / `TSP207` 免驱 USB 音频，不降低 SIP |
| 显卡 (`RX 9060 XT` `1002:7590`) | `VERIFIED_HOST_ONLY` (解析与 ABI) / `BLOCKED` (真机加速) | 安装期使用 UEFI GOP；Gate D 阶段分步测试 `AMDRadeonRDNA4-Navi44` 与 `Cobalt64` |
