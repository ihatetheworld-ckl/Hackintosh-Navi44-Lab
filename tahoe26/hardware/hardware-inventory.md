# Windows 主机硬件普查报告 (Hardware Inventory)

- **核查日期**：2026-10-26
- **核查方式**：Windows 注册表 (`HKLM:\HARDWARE`、`HKLM:\SYSTEM\CurrentControlSet\Enum`)、`pnputil`、Win32 `GlobalMemoryStatusEx`、`.NET DriveInfo`、`mountvol`（全程只读，零硬件/固件/磁盘写入）
- **证据等级**：`VERIFIED_REAL_HARDWARE`（Windows Host 只读枚举）

---

## 1. CPU 与平台拓扑

| 项目 | 实测值 | 证据来源 | macOS 26 Tahoe 适配影响 |
|---|---|---|---|
| 处理器型号 | `12th Gen Intel(R) Core(TM) i5-12600KF` | `HKLM:\HARDWARE\DESCRIPTION\System\CentralProcessor\0` | Alder Lake 混合架构，需 Faker CPUID (`0x0A0655` Comet Lake) |
| CPU 标识 | `Intel64 Family 6 Model 151 Stepping 2` (`0x069702`) | CentralProcessor Registry | 原生内核无 Alder Lake Family/Model 分支，需 OpenCore `Cpuid1Data`/`Cpuid1Mask` |
| 逻辑处理器数量 | `16` Logical Processors (6 P-Cores × 2 SMT + 4 E-Cores × 1) | `CentralProcessor\0..15` | 启用全部核时需配合 `CpuTopologyRebuild.kext` 与 `ProvideCurrentCpuInfo = true` |
| 基准频率 | `3686 MHz` (~3.7 GHz) | `~MHz` Registry | XCPM 原生电源管理需 `AppleXcpmCfgLock`（若 BIOS 未解锁 CFG Lock）+ `CPUFriend.kext` |
| 核显 (iGPU) | **无**（KF 后缀无核显，PCI 总线无 `8086:4680`/`4690` 设备） | PCI 全量枚举 | **无法使用核显输出或过渡**；所有显示输出 100% 依赖独立显卡 RX 9060 XT |

---

## 2. 主板、BIOS 与固件安全状态

| 项目 | 实测值 | 证据来源 | 状态 / 备注 |
|---|---|---|---|
| 主板制造商 | `Maxsun` (铭瑄) | `HKLM:\HARDWARE\DESCRIPTION\System\BIOS` | 铭瑄主板 ACPI 命名规范：`PC00` 根桥 |
| 主板型号 | `MS-Terminator B760M D5` (终结者 B760M D5) | `BaseBoardProduct` / `SystemProductName` | Intel B760 芯片组 (`8086:7Axx` PCH)，DDR5 平台 |
| BIOS 厂商与版本 | `American Megatrends International, LLC.` / `E1.5D` (Release 5.27) | `BIOSVendor` / `BIOSVersion` | 发布日期：`08/13/2024` |
| 启动模式 | `UEFI` | `UEFISecureBootEnabled` 键存在 | 支持 GPT + 独立 ESP 引导 |
| Secure Boot | **已关闭 (`0`)** | `HKLM:\...\Control\SecureBoot\State` (`UEFISecureBootEnabled = 0`) | 符合 OpenCore 与自定义驱动引导前置条件 |
| TPM 状态 | 已启用 (`ACPI\MSFT0101\1`, Firmware `600.18.30.2255`) | `HKLM:\...\Services\TPM` | **严禁关闭或清除 TPM**，以保护 Windows 10 IoT LTSC 2024 登录与安全基线 |
| 物理内存 | `34,186,244,096 bytes` (~32 GB DDR5) | `GlobalMemoryStatusEx` | 容量充足 |
| ACPI 原始表签名 | `DSDT` (`ALASKA A_M_I_ 01072009`), `FADT`, `RSDT`, `SSD1` (`CpuSsdt`), `SSD2` (`SaSsdt`), `SSD3` (`IgfxSsdt`), `SSD4` (`Ther_Rvp`), `SSD5` (`PtidDevc`), `SSD6` (`TbtTypeC`), `SSD7` (`UsbCTabl`), `SSD8` (`xh_rps14`), `SSD9` (`SocGpe`), `SSDA` (`SocCmn`), `SSDT` (`Pmax_Dev`) | `HKLM:\HARDWARE\ACPI` | 提供了完整的表签名，指导 SSDT-EC、SSDT-PLUG-ALT、SSDT-USBX、SSDT-RTCAWAC 编写 |
| CFG Lock / VT-d / Above 4G / ReBAR | `UNKNOWN` (Windows 用户态只读无法直接确证 MSR `0xE2` 锁状态；但 GPU visible BAR 记录与 16GB VRAM 对应) | BIOS / MSR 未知 | OpenCore 默认开启 `AppleXcpmCfgLock = true` 兜底；VT-d 由 `DisableIoMapper` 或 `AppleVTD` 策略控制 |

---

## 3. 独立显卡 (AMD Radeon RX 9060 XT / Navi 44)

| 项目 | 实测值 | 证据来源 | 说明 |
|---|---|---|---|
| 设备名称 | `AMD Radeon RX 9060 XT` | `PCI\VEN_1002&DEV_7590&SUBSYS_24381458&REV_C0` | RDNA 4 架构 / Navi 44 / `gfx1200` |
| Vendor / Device ID | `1002:7590` | PCI Enum | 与 `Hackintosh-Navi44-Lab` 的 `Asic::identify(0x1002, 0x7590)` 完全匹配 |
| Subsystem ID | `1458:2438` (Gigabyte 技嘉子系统 ID) | PCI Enum (`SUBSYS_24381458`) | 首次核实具体板卡厂商为技嘉 (Gigabyte `0x1458`) |
| Revision ID | `0xC0` (`REV_C0`) | PCI Enum | 首次核实真实硬件 Revision ID 为 `0xC0` |
| PCIe 拓扑路径 | Bus 0 (`8086:460D` PEG10 `(0,1,0)`) → Bus 1 (`1002:1478` Upstream Switch `(1,0,0)`) → Bus 2 (`1002:1479` Downstream Switch `(2,0,0)`) → **Bus 3 (`1002:7590` GPU `(3,0,0)` + `1002:AB40` HDMI/DP Audio `(3,0,1)`)** | PCI LocationInformation | 极其关键：显卡位于三层 PCI 桥之后 (`PC00.PEG0.PEGP.SWUS.SWDS.GFX0`)，DeviceProperties 注入若按路径必须匹配三层桥 |
| 显存容量 (VRAM) | `17,095,983,104 bytes` (~16 GB) | `HardwareInformation.qwMemorySize` | 16 GB GDDR6 显存版本 |
| VBIOS 字符串 | `113-R906XGOI-F1` | `HardwareInformation.BiosString` | 只读注册表记录（未读取 GPU ROM 硬件） |
| Windows 驱动版本 | `32.0.31035.1003` (`oem16.inf`) | Display Class Registry | Windows 主系统下工作正常 |
| 连接显示器 | `HKC2410` (`DISPLAY\HKC2410\7&d0c0685&0&UID260`) | `HKLM:\SYSTEM\CurrentControlSet\Enum\DISPLAY` | 高刷电竞显示器（对应 1440p 高刷 DisplayID 场景） |

---

## 4. 网络、音频、USB 与外设概览

| 类别 | 设备描述 | 硬件 ID | PCI / USB 位置 |
|---|---|---|---|
| 有线网卡 | Realtek Gaming 2.5GbE Family Controller (RTL8125) | `PCI\VEN_10EC&DEV_8125&SUBSYS_012310EC&REV_05` | PCI Bus 7, Dev 0, Func 0 (位于 PCH RP `8086:7A36` `(0,29,0)` 下) |
| 无线网卡 | Intel(R) Wi-Fi 6 AX101 (CNVi) | `PCI\VEN_8086&DEV_7A70&SUBSYS_02448086&REV_11` | PCI Bus 0, Dev 20, Func 3 `(0,20,3)` |
| 蓝牙 | Intel(R) Wireless Bluetooth(R) | `USB\VID_8087&PID_0026\5&2ffde795&0&14` | 内置 USB 端口 14 (`HS14`) |
| 板载声卡控制器 | Intel B760 High Definition Audio Controller | `PCI\VEN_8086&DEV_7A50&SUBSYS_089710EC&REV_11` | PCI Bus 0, Dev 31, Func 3 `(0,31,3)` |
| 板载音频 Codec | Realtek ALC897 | `HDAUDIO\FUNC_01&VEN_10EC&DEV_0897&SUBSYS_10EC0897&REV_1004` | HDAUDIO Bus |
| 显卡音频控制器 | AMD RDNA4 High Definition Audio Bus | `PCI\VEN_1002&DEV_AB40&SUBSYS_AB401002&REV_00` (`HDAUDIO\FUNC_01&VEN_1002&DEV_AA01`) | PCI Bus 3, Dev 0, Func 1 `(3,0,1)` |
| USB 音频外设 | TSP207 麦克风 / Philips SPA3609 USB | `USB\VID_3769&PID_B020` / AudioEndpoint | USB Audio Class (免驱) |
| 原生 USB 控制器 | Intel USB 3.20 eXtensible Host Controller | `PCI\VEN_8086&DEV_7A60&SUBSYS_07606688&REV_11` | PCI Bus 0, Dev 20, Func 0 `(0,20,0)` |
| 附加 USB 控制器 | ASMedia ASM2142 / ASM3142 USB 3.1 xHCI Controller | `PCI\VEN_1B21&DEV_2142&SUBSYS_21421B21&REV_00` | PCI Bus 5, Dev 0, Func 0 (位于 PCH RP `8086:7A38` `(0,28,0)` 下) |
| 主板 RGB 控制器 | ENE/Maxsun MS-ARGB | `USB\VID_0CF2&PID_7750` | 内置 USB 2.0 端口 |
| 外接 Type-C 扩展坞 | Xiaomi Type-C 5-in-1 Hub | `USB\VID_5059&PID_5059` | 外接 USB 端口 |
