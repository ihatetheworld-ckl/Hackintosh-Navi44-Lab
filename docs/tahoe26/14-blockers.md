# 14 — 当前三大核心技术阻碍与应对方案 (Remaining Blockers)

## 阻碍一：AMD Radeon RX 9060 XT (`1002:7590` / Navi 44 / `gfx1200`) 无原生 macOS 驱动，且开源 RDNA4 项目目前仅在 Navi 48 (`1002:7550`) 上实测
- **技术本质**：macOS 26 Tahoe 官方 AMD GPU 驱动最高仅支持到 RDNA 2 (`Navi 21/22/23`)。社区开源项目 `RX4Darwin/AMDRadeonRDNA4.kext` 与 `Almosst-DEV/Cobalt64` 虽已打通 RDNA 4 的部分显示与 RADV/Metal 实验链路，但其固件引用（`gc_12_0_1`）、`GB_ADDR_CONFIG` 校验与 PCI ID 均绑定在 `Navi 48` (`gfx1201`)。
- **应对方案**：
  1. **安装与基础桌面阶段**：利用 RX 9060 XT 的 UEFI GOP Framebuffer 直接完成 macOS 26 安装与基础桌面运行（禁用冲突的 `WhateverGreen.kext`）。
  2. **驱动研发阶段**：本轮已完成 DisplayID v1.3/v2.0 (`2560x1440@180Hz`) 解析与 `N44Q -> Cobalt 192B` 候选投影协议（`171 PASS`）。下一步先在您的真实 Apple Mac 上完成 Mach-O `x86_64` 原生编译（M6），再在 Gate D 授权下分步采集本卡 IP Discovery (`GC 12.0.0`) 与 AtomBIOS 数据，渐进验证 Framebuffer → Vulkan → Metal。

## 阻碍二：macOS 26 Tahoe 移除原生 `AppleHDA.kext`，导致板载 Realtek `ALC897` (`10EC:0897`) 传统 `AppleALC` 注入失效
- **技术本质**：Apple 在 macOS 26 Tahoe 中移除了 `AppleHDA.kext`，若强行向系统卷回写 `AppleHDA.kext` 或安装 `VoodooHDA.kext`，必须降低 SIP（System Integrity Protection）与根卷密封保护，违背本工程第 9.4 节“不得为了模拟音频默认降低整个 macOS 系统安全保护”的原则。
- **应对方案**：
  1. **零妥协首选方案**：本机硬件普查已确认连接有 **USB 音频设备 (`Philips SPA3609 USB` 与 `TSP207` `USB\VID_3769&PID_B020`)**，macOS 26 Tahoe 原生 `AppleUSBAudio` 对 USB Audio Class 设备 100% 免驱即插即用，无需降低任何 SIP 安全保护即可直接获得音频输入与输出！
  2. **备选方案**：待 GPU DCN4 显示引擎打通后启用 DP/HDMI 数字音频，或在用户显式批准修改 SIP 的前提下单独评估 `SimpleHDA`/`AppleHDA` 恢复方案。

## 阻碍三：Intel Wi-Fi 6 `AX101` (`8086:7A70`) 为 CNVi 1x1 精简卡，且目标盘 `INTEL SSDPEKKF256G8L` 存在旧 Linux 分区
- **技术本质**：
  1. `8086:7A70` (`AX101`) 属于 Alder Lake/Raptor Lake PCH CNVi 接口的 1x1 Wi-Fi 6 网卡，相比独立 PCIe 的 AX200/AX210，CNVi 卡在 macOS 26 下的固件握手更容易受版本影响。
  2. 目标 256GB SSD (`INTEL SSDPEKKF256G8L`) 实测包含两个旧分区（1.05GiB + 237.4GiB，疑似旧 Linux），在未获 Gate C 授权前不可清盘。
- **应对方案**：
  1. 网络优先启用 100% 稳定支持 `10EC:8125` 的 `LucyRTL8125Ethernet.kext` (2.5GbE 有线网卡) 完成安装与日常主力联网；`AX101` Wi-Fi 与 `8087:0026` 蓝牙在候选 `config.plist` 中已预置条目（默认 `Enabled = false`），待基础系统就绪后单独开启验证。
  2. 提供清空旧 Linux 全盘安装 macOS 26（方案 A）与缩小旧 Linux 分区共存（方案 B）供您在 Gate C 确认。
