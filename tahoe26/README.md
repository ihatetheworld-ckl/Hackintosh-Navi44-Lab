# PROJECT TAHOE26 — 全自动黑苹果双系统与 Navi44 驱动适配工程

> **当前阶段**：M0–M5（离线安全研发、主机硬件普查、上游技术选型、OpenCore 候选工程与 Navi44 DisplayID/ABI 增强已完成；等待 Gate B/C/D 及真实 Mac 构建授权）
> **安全边界**：Gate A（Windows 主系统只读保护，零磁盘写入，零 GPU 硬件/MMIO/BAR 访问，零 Kext 加载）

## 目录结构

| 路径 | 说明 |
|---|---|
| `PROJECT_STATE.md` | 持久化项目状态、硬件基线、Git 状态、已完成工作与门禁状态 |
| `NEXT_ACTIONS.md` | 本轮完成清单、修改文件、测试证据、下一步自动研发与待确认授权清单 |
| `hardware/` | Windows 主机只读硬件普查清单（CPU/主板/PCI/存储/兼容性/Windows 保护基线） |
| `compatibility/` | macOS 26 Tahoe 硬件兼容性矩阵与技术选型表 |
| `opencore/` | 针对 i5-12600KF + MAXSUN B760M D5 的候选 OpenCore 1.0.8 EFI 结构、ACPI DSL 源码与 `config.plist` |
| `drivers/` | Navi44 (`1002:7590`)、平台、网络、音频、USB 驱动研发与配置清单 |
| `research/` | RDNA4 (`gfx1200` vs `gfx1201`)、Cobalt64、Mesa RADV、Metal 架构差距研究 |
| `scripts/` | 默认 Dry-Run 的安全辅助工具（硬件核查、OpenCore 候选校验、Mac 原生构建交接脚本） |
| `tests/` | Host / Mock / Native / Hardware 实验计划与验证记录 |
| `recovery/` | Windows 主盘零触碰保护与双系统独立 EFI 恢复手册 |
