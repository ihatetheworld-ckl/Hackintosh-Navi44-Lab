# 00 — 项目总览与工程架构 (Project Overview)

- **工程代号**：`PROJECT TAHOE26`
- **当前分支**：`tahoe26-dev`（基于 `main` 提交 `6b088ba` 建立的独立开发分支，不覆盖原历史记录）
- **目标操作系统**：原生 `macOS 26 Tahoe` (`Darwin 25.x`, `x86_64` 末代 Intel 支持版)
- **核心安全铁律**：Windows 主系统盘（`WD_BLACK SN850X 2000GB`, `PCI\VEN_15B7&DEV_5030` @ Bus 4）只读保护高于一切；采用双独立物理 NVMe SSD + 双独立 EFI System Partition 架构。
- **核心研发重点**：结合 `RX4Darwin/AMDRadeonRDNA4.kext` 与 `Almosst-DEV/Cobalt64` 持续攻关 `AMD Radeon RX 9060 XT` (`1002:7590`, Navi 44, `gfx1200`) 在 macOS 26 下的显示输出、RADV Vulkan 与 Metal 加速。

详见：
- [01-hardware-inventory.md](01-hardware-inventory.md)
- [02-compatibility-matrix.md](02-compatibility-matrix.md)
- [03-upstream-audit.md](03-upstream-audit.md)
- [04-cpu-acpi.md](04-cpu-acpi.md)
- [05-opencore.md](05-opencore.md)
- [06-navi44-driver.md](06-navi44-driver.md)
- [07-native-build.md](07-native-build.md)
- [08-installer-preparation.md](08-installer-preparation.md)
- [09-dual-boot-design.md](09-dual-boot-design.md)
- [10-install-guide.md](10-install-guide.md)
- [11-hardware-tests.md](11-hardware-tests.md)
- [12-recovery-guide.md](12-recovery-guide.md)
- [13-security-audit.md](13-security-audit.md)
- [14-blockers.md](14-blockers.md)
- [15-project-progress.md](15-project-progress.md)
