# 03 — 上游项目实时审计 (Upstream Audit — 2026-10)

详见 [compatibility-inventory.md](../../tahoe26/hardware/compatibility-inventory.md) 第 2 节与根目录 [UPSTREAM_SOURCES.md](../../UPSTREAM_SOURCES.md)。

## 关键发现
1. **OpenCorePkg v1.0.8 (2026-09-27)** 与 **Lilu v1.7.2 (2026-03-20)**、**VirtualSMC v1.3.8 (2026-09)** 已正式支持 macOS 26 Tahoe (`Darwin 25.x`)，无需 `-lilubetaall`。
2. **macOS 26 Tahoe 移除了 `AppleHDA.kext`**：传统仅靠 `AppleALC.kext` 的板载模拟音频方案在 Tahoe 下不再开箱即用；强行恢复 `AppleHDA` 或使用 `VoodooHDA` 需降低 SIP。本机已配备 USB 声卡/麦克风（`Philips SPA3609 USB`、`TSP207`），可直接通过原生 `AppleUSBAudio` 完美工作且保持完整 SIP 安全保护。
3. **`WhateverGreen.kext` 与 RDNA4 驱动冲突**：`WhateverGreen` 仅支持到 RDNA2 (`Navi 2x`)，若启用会拦截 `1002:xxxx` PCI 设备并破坏 `AMDRadeonRDNA4.kext` 初始化。因此在候选 `config.plist` 中已将 `WhateverGreen.kext` 明确设为 `Enabled = false`。
4. **`RX4Darwin/AMDRadeonRDNA4.kext` 与 `Almosst-DEV/Cobalt64`**：
   - 上游主线目前在 RX 9070 XT (`Navi 48`, `1002:7550`, `gfx1201`) 上验证了单 DP 60fps 桌面合成与 RADV/Metal 实验路线。
   - 尚未发布针对 RX 9060 XT (`Navi 44`, `1002:7590`, `gfx1200`) 的开箱即用 Release 二进制。
   - 本工程基于本地已固定的两套上游源码（保留于 `D:\CodexWorkSpace\黑苹果研究\Hackintosh-Navi44-Lab\upstream` 及本工作区 `development/AMDRadeonRDNA4-Navi44`）继续推进 `gfx1200` 适配。
