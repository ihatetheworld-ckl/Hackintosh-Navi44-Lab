# 15 — 项目里程碑进度总表 (Project Progress — M0..M12)

| 里程碑 | 阶段名称 | 当前状态 | 证据等级 | 关键产出 |
|---|---|---|---|---|
| **M0** | 项目接管与基线核验 | **COMPLETED** | `VERIFIED_HOST_ONLY` | 接管 `Hackintosh-Navi44-Lab`，创建独立分支 `tahoe26-dev`，保留全部 M6–M8.5 历史与许可证 |
| **M1** | Windows 主机只读硬件普查 | **COMPLETED** | `VERIFIED_REAL_HARDWARE` | 完成 CPU/主板/BIOS/PCI/USB/双 NVMe 分区偏移普查，输出 `tahoe26/hardware/*.md` |
| **M2** | 实时上游技术调研 (2026-10) | **COMPLETED** | `UPSTREAM_REPORTED` | 核实 OpenCore 1.0.8、Lilu 1.7.2、VirtualSMC 1.3.8、Tahoe `AppleHDA` 移除、RDNA4 上游进展 |
| **M3** | 兼容性决策与技术路线制定 | **COMPLETED** | `VERIFIED_HOST_ONLY` | 确立路线 A/B/C 组合策略与 9 阶段现实边界定义 |
| **M4** | OpenCore 1.0.8 候选工程构建 | **COMPLETED** | `VERIFIED_HOST_ONLY` | 生成 4 份定制 ACPI DSL、`UTBMap.kext`、`config.plist`，通过离线校验 (`12/12 PASS`) |
| **M5** | Navi44 Host 驱动研发演进 | **COMPLETED** | `VERIFIED_HOST_ONLY` | 新增 DisplayID v1.3/v2.0 (`1440p@180Hz`) 解析与 `N44Q -> Cobalt 192B` 投影；C++ `171 PASS`，Fuzz `4000` 组 PASS，Clang 静态分析零警告 |
| **M6** | Apple Mac 原生构建验证 | **READY FOR MAC EXECUTION** | `UNVERIFIED` (脚本已就绪) | 已生成 `tahoe26/scripts/run_mac_native_verification.py`，待在用户真实 Mac 上执行 |
| **M7** | 安装候选包与恢复预案准备 | **COMPLETED (Offline)** | `VERIFIED_HOST_ONLY` | 完成安装指南、双盘隔离设计（含 `SSDT-NVME-PROTECT`）与恢复指南 |
| **M8** | 安装介质制作与启动验证 | **WAITING FOR GATE B** | `BLOCKED` (需 Gate B 授权) | 待用户确认安装 U 盘设备与擦除授权 |
| **M9** | 第二块独立 SSD (`INTEL 256G`) 安装 | **WAITING FOR GATE C** | `BLOCKED` (需 Gate C 授权) | 待用户确认 `INTEL SSDPEKKF256G8L` 旧 Linux 分区处置方案与写盘授权 |
| **M10** | Navi44 真机驱动渐进式实验 | **WAITING FOR GATE D** | `BLOCKED` (需 Gate D 授权) | 已制定 Exp 1..9 安全边界与回退机制 |
| **M11** | 双系统独立启动与全功能联合验收 | **PENDING M9/M10** | `UNVERIFIED` | 待安装后逐项实测 |
| **M12** | 最终正式交付 | **IN PROGRESS** | `PARTIAL` | 持续累积可复现源码、测试与文档 |
