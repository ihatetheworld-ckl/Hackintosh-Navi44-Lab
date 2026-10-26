# 本机硬件 macOS 26 Tahoe 兼容性矩阵与上游技术选型 (Compatibility Inventory)

- **审计日期**：2026-10-26
- **目标系统**：macOS 26 Tahoe (`Darwin 25.x`, `x86_64` 末代 Intel 支持版本)

---

## 1. 全机硬件逐项兼容性矩阵

| 子系统 | 本机硬件型号 | 精确硬件 ID | macOS 26 适配方案 | 当前状态分级 | 可达功能阶段与核心风险说明 |
|---|---|---|---|---|---|
| **CPU** | Intel Core i5-12600KF (6P+4E, 16T) | `CPUID 0x069702` | OpenCore `Cpuid1Data` 伪装 Comet Lake (`0x0A0655`) + `CpuTopologyRebuild.kext` + `CPUFriend.kext` + `ProvideCurrentCpuInfo=true` | `UPSTREAM_REPORTED` / `VERIFIED_HOST_ONLY` | **Daily Driver 可达**：无需关闭 E-Core；提供保留 6P+4E 全核方案与仅 6P 备用方案 |
| **主板 / 芯片组** | 铭瑄 MS-Terminator B760M D5 (BIOS `E1.5D`) | `8086:7A06` (LPC), `8086:7A23` (SMBus) | `SSDT-EC` + `SSDT-RTCAWAC` + `SSDT-PLUG-ALT` + `SSDT-USBX` + `AppleXcpmCfgLock` | `VERIFIED_HOST_ONLY` | **Daily Driver 可达**：Secure Boot 已实测为 `0` (Disabled) |
| **目标 NVMe** | Intel Pro 7600p 256GB (`INTEL SSDPEKKF256G8L`) | `8086:F1A6` (Rev `03`, Bus 6) | macOS 原生 `IONVMeFamily.kext` | `UPSTREAM_REPORTED` | **Daily Driver 可达**：SMI/Intel 主控对 macOS 兼容性极佳，无 PM981/SN750 类 Panic 问题 |
| **主系统 NVMe** | WD_BLACK SN850X 2000GB (Windows 10 LTSC) | `15B7:5030` (Rev `01`, Bus 4) | 安装期通过 `SSDT-NVME-PROTECT` / DeviceProperties `IOName=#disabled` 屏蔽，彻底防误触 | `VERIFIED_REAL_HARDWARE` | **100% 保护隔离**：安装期对 macOS 不可见 |
| **有线网卡** | Realtek Gaming 2.5GbE (RTL8125) | `10EC:8125` (Subsys `10EC:0123`, Rev `05`, Bus 7) | `LucyRTL8125Ethernet.kext` (`v1.2.2`) | `UPSTREAM_REPORTED` | **Daily Driver 可达**：支持 DHCP/IPv4/IPv6/2.5GbE，可作为 Recovery 在线或离线安装后主力网络 |
| **无线网卡** | Intel Wi-Fi 6 AX101 (CNVi) | `8086:7A70` (Subsys `8086:0244`, Rev `11`, Bus 0) | 方案 1：`itlwm.kext` + `HeliPort.app`（最稳，不改 SIP）<br>方案 2：Tahoe 分支 `AirportItlwm.kext` | `UNVERIFIED` (针对 `7A70` 1x1 CNVi) | **需真机验证**：`AX101` (`7A70`) 为 CNVi 1x1 精简卡，上游 `itlwm` 对 AX201/AX211 支持成熟，但 `7A70` 固件加载需真机实测；有线网卡 `RTL8125` 为可靠兜底 |
| **蓝牙** | Intel Wireless Bluetooth | `USB\VID_8087&PID_0026` | `IntelBluetoothFirmware.kext` + `IntelBTPatcher.kext` + `BlueToolFixup.kext` + `-ibtcompatbeta` | `UPSTREAM_REPORTED` | **可用**：`8087:0026` (AX201/AX101 同款 USB PID) 在 `OpenIntelWireless` 中有明确固件表匹配 |
| **USB 控制器** | Intel B760 XHCI + ASMedia ASM2142 | `8086:7A60` (Bus 0) + `1B21:2142` (Bus 5) | 原生 `AppleUSBXHCIPCI` + `USBToolBox.kext` + 本机定制 `UTBMap.kext` | `VERIFIED_HOST_ONLY` | **Daily Driver 可达**：不长期依赖 `XhciPortLimit`，使用 USBToolBox 精确映射 15 端口以内 |
| **音频 (USB)** | TSP207 USB 麦克风 / Philips SPA3609 USB | `USB\VID_3769&PID_B020` | macOS 原生 `AppleUSBAudio` (UAC 免驱) | `UPSTREAM_REPORTED` | **立即可用，零 SIP 风险**：本机已连接 USB 音频设备，在 Tahoe 下免驱即插即用 |
| **音频 (板载)** | Realtek ALC897 | `10EC:0897` (Subsys `10EC:0897`, HDA `8086:7A50`) | Tahoe 移除了原生 `AppleHDA.kext`，传统 `AppleALC` 单独注入失效；需 `SimpleHDA`/AppleHDA 恢复方案或 `VoodooHDA` | `BLOCKED` (不降级 SIP 时) | **优先使用本机现有 USB 音频 (Philips SPA3609 / TSP207)**；遵守第 9.4 节“不因模拟音频默认降低整个系统安全保护”原则 |
| **独立显卡 (GPU)** | **AMD Radeon RX 9060 XT 16GB (Gigabyte)** | **`1002:7590` (Subsys `1458:2438`, Rev `C0`, Bus 3)** | **阶段 1**：UEFI GOP 帧缓冲驱动桌面 (Bootable / Installable / Unaccelerated Desktop)<br>**阶段 2**：`AMDRadeonRDNA4-Navi44` (Framebuffer/Display/MMIO)<br>**阶段 3**：`Cobalt64` (RADV Vulkan + Metal translation) | **`BLOCKED` (Metal/3D 加速尚未在 Navi44 真机实现)** | **最大技术难关**：macOS 无原生 RDNA4 驱动；开源 `AMDRadeonRDNA4` / `Cobalt64` 目前仅针对 Navi48 (`1002:7550` RX 9070 XT) 做过真机实验，Navi44 (`1002:7590`) 需本工程持续移植与真机分步验证 |

---

## 2. 上游核心组件版本与来源审计表 (Section 4.8)

| 组件名称 | 上游仓库 URL | 选定版本 / Commit Pin | 许可证 | 适用范围与兼容风险说明 |
|---|---|---|---|---|
| **OpenCorePkg** | `https://github.com/acidanthera/OpenCorePkg` | `v1.0.8` (2026-09-27) | BSD-3-Clause | 原生支持 macOS 26 Tahoe 引导、`macrecovery` 与 `edk2-stable-202511` |
| **Lilu** | `https://github.com/acidanthera/Lilu` | `v1.7.2` (2026-03-20) / Pin `0515f40b...` | BSD-3-Clause | 无需 `-lilubetaall` 即可在 macOS 26 Tahoe 加载，修复现代内核地址槽溢出 |
| **VirtualSMC** | `https://github.com/acidanthera/VirtualSMC` | `v1.3.8` (2026-09) | BSD-3-Clause | 修复 macOS 15.4+ 及 Tahoe 下 `PerfPowerServices` 冻结问题 |
| **WhateverGreen** | `https://github.com/acidanthera/WhateverGreen` | **默认禁用 / 隔离** (`Enabled = false`) | BSD-3-Clause | **关键冲突警告**：WhateverGreen 针对 RDNA2 及更早架构设计，会对 `1002:xxxx` 显卡执行 legacy framebuffers/CAIL 补丁，与 `AMDRadeonRDNA4.kext` 冲突，候选配置中**禁止默认启用** |
| **LucyRTL8125Ethernet** | `https://github.com/Mieze/LucyRTL8125Ethernet` | `v1.2.2` (2025-02-16) | GPL-2.0 | 针对 `10EC:8125` 2.5GbE 网卡，修复 `IOFree()` 崩溃，兼容 Tahoe |
| **CPUFriend** | `https://github.com/acidanthera/CPUFriend` | `v1.3.0+` | BSD-3-Clause | 配合 `CPUFriendDataProvider` 优化 i5-12600KF XCPM 频率向量 |
| **CpuTopologyRebuild** | `https://github.com/b00t0x/CpuTopologyRebuild` | Latest Release | BSD-3-Clause | 修复 Alder Lake 6P+4E 大小核 SMT 拓扑识别 |
| **USBToolBox** | `https://github.com/USBToolBox/kext` | `v1.2.0` (2025-06-13) | MIT | 支持 Tahoe 下通过 `UTBMap.kext` 进行无代码端口映射 |
| **itlwm / IntelBluetooth** | `https://github.com/OpenIntelWireless/itlwm` | `v2.3.0+` / Tahoe Fork | GPL-2.0 | 为 `8086:7A70` (AX101) 与 `8087:0026` (BT) 提供候选驱动（默认在 `config.plist` 中设为可选启用，避免首次安装因 CNVi 固件引起卡死） |
| **AMDRadeonRDNA4.kext** | `https://github.com/RX4Darwin/AMDRadeonRDNA4.kext` | Fixed Pin `49f7f20c00dd154384418078f8a09e79c400a06a` | BSD-3-Clause (局部 MIT) | 本仓库 `development/AMDRadeonRDNA4-Navi44` 的直接上游基线 |
| **Cobalt64** | `https://github.com/Almosst-DEV/Cobalt64` | Fixed Pin `d6c9aedf8e6526a39e349b5886cbc8c7ddf77f65` | MIT (按子目录) | RDNA4 Darwin RADV Vulkan 与 `metal2vulkan` 转换层参考基线 |
| **MacKernelSDK** | `https://github.com/acidanthera/MacKernelSDK` | Fixed Pin `05094e5e88cec7caedbfb35e8449ed0db94bf95b` | Mixed Apple APSL / BSD | 供 Apple Mac 真机编译 Kext Target 时使用的固定内核头文件 |

---

## 3. macOS 26 Tahoe 可行性边界与三条技术路线 (Chapter 5)

### 3.1 阶段现实边界定义与当前可达性评估

| 阶段 | 定义 | 本机可达性评估 | 依赖条件 / 阻碍 |
|---|---|---|---|
| **1. Bootable** | 进入 OpenCore 菜单并引导 macOS 26 内核 | **高可行 (READY TO TEST IN GATE B)** | OpenCore 1.0.8 + Alder Lake CPUID 仿冒 + ACPI SSDT + UEFI GOP |
| **2. Installable** | 在 `INTEL SSDPEKKF256G8L` 上完成 macOS 26 安装 | **高可行 (READY FOR GATE C)** | `IONVMeFamily` 原生支持 Intel 256GB SSD + `LucyRTL8125Ethernet` 有线网络 |
| **3. Desktop** | 进入 macOS 26 桌面环境 | **高可行** | 通过 UEFI GOP Framebuffer 提供基本图形桌面（无硬件 3D 加速） |
| **4. Display** | 原始分辨率 / EDID 识别 / 多模式输出 | **研发中 (`VERIFIED_HOST_ONLY`)** | M8 + 本轮 M9 已完成 EDID / DisplayID (含 `2560x1440@180Hz`) / AtomBIOS 解析，需 Gate D 真机读取 ROM/Discovery 并接管 DCN4.x HUBP/OTG |
| **5. Accelerated 2D** | WindowServer 帧缓冲扫描输出 (Scanout) | **中长期攻关 (`UNVERIFIED`)** | 需将 `AMDRadeonRDNA4` 的 `N48N_SEL_SCAN_*` 从 Navi48 (`gfx1201`) 移植到 Navi44 (`gfx1200`) |
| **6. GPU Compute** | GFX12 队列初始化、固件加载与计算 Shader 执行 | **中长期攻关 (`BLOCKED` 缺真机 Discovery/Firmware)** | 需真机 IP Discovery、PSP/SMU/GC 12.0.0 固件加载、GART/VM 页表与 GFX12 环初始化 |
| **7. Vulkan** | Mesa RADV Darwin Backend 创建 `VkDevice` 并渲染 | **中长期攻关 (`VERIFIED_HOST_ONLY` 仅协议层)** | 本轮已实现 `N44Q -> 192B CobaltQueryProjection`，需修改 RADV Darwin Winsys 移除 `ACD_GB_ADDR_CONFIG_GFX1201` 硬编码检查 |
| **8. Metal** | macOS Metal API 与 WindowServer 完整合成加速 | **`BLOCKED`（核心远期攻关）** | 依赖 `Cobalt64` 的 `IOAccelNavi48NativeClient` + `Navi48MetalNub` + `metal2vulkan` 转换栈在 `gfx1200` 与 Tahoe `WindowServer` 下的适配 |
| **9. Daily Driver** | 睡眠唤醒、多屏高刷、全功能硬件加速日常稳定运行 | **`PARTIAL`（基础系统可达，GPU 加速待突破）** | 若 GPU Metal 暂未完全打通，系统仅能作为 VESA/GOP 桌面或研发测试机使用，绝不虚假宣传为完美日常机 |

### 3.2 三条执行路线组合策略
1. **路线 A（直接复用成熟开源方案）**：用于 **CPU (i5-12600KF)、主板 (B760M)、NVMe (Intel 256G)、有线网络 (RTL8125)、蓝牙 (8087:0026)、USB 音频 (SPA3609/TSP207)**。直接采用 OpenCore 1.0.8 + Acidanthera/Mieze 官方成熟组件，不重复造轮子。
2. **路线 B（现成方案 + 最小改动）**：用于 **OpenCore ACPI/USB 定制** 与 **AMDRadeonRDNA4 / Cobalt64 公共 RDNA4 基础设施复用**。保留上游 AtomBIOS、EDID、IP Discovery、ELF CodeObj 与 `N48N` 通信框架，仅针对 `1002:7590` (`gfx1200`) 分离设备特性。
3. **路线 C（针对 Navi44 的专门驱动研发）**：用于 **DisplayID 高刷模式解析、`N44Q -> Cobalt 192B` 安全投影协议、以及后续 Mac 原生 Kext 构建与 Gate D 分步硬件实验**。
