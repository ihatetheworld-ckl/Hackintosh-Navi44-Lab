# 13 — 安全与合规审计报告 (Security & Safety Audit — Gate A)

- **审计时间**：2026-10-26
- **授权等级**：**Gate A**（安全研究与离线开发）

| 审计项目 | 本轮实际执行状态 | 证据说明 |
|---|---|---|
| Windows 主盘 (`WD_BLACK SN850X`) 分区/EFI/BCD 修改 | **零修改 (`NOT TOUCHED`)** | 仅通过注册表与 `pnputil` 只读查询枚举 |
| 目标盘 (`INTEL SSDPEKKF256G8L`) 分区/格式化 | **零写入 (`NOT TOUCHED`)** | 已识别存在 1.05GiB + 237.4GiB 旧分区，等待用户 Gate C 授权 |
| USB 存储设备 (`E:\` Generic Masstorage) 写入 | **零写入 (`NOT TOUCHED`)** | 等待用户 Gate B 授权 |
| BIOS / UEFI / TPM / Secure Boot / BitLocker 变更 | **零变更 (`NOT TOUCHED`)** | 只读确认 `UEFISecureBootEnabled = 0`，TPM 保持原样 |
| GPU (`1002:7590`) ROM / BAR / MMIO / DMA 访问 | **零访问 (`NOT TOUCHED`)** | 未读取硬件 ROM，未映射 BAR，未安装任何内核驱动 |
| 全局 PATH / 全局 Git 配置修改 | **零修改 (`NOT TOUCHED`)** | 直接使用绝对路径调用既有 Python 3.12.13 与 Clang 23.1.3 |
| 敏感信息 / 序列号 / Token 泄露防控 | **已通过审计** | `config.plist` 中 SMBIOS 使用 `PLACEHOLDER_LOCAL_SN`，磁盘序列号已脱敏，未包含任何 Token |
| 上游开源许可证保留 | **已通过审计** | `BSD-3-Clause`、`MIT`、`Apache-2.0 WITH LLVM-exception` 完整保留 |
