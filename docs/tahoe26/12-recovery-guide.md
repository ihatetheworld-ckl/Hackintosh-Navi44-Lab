# 12 — Windows 与 macOS 双系统故障恢复指南 (Recovery Guide — Chapter 15 & 18)

## 1. 恢复场景一：macOS 启动卡死 / Kernel Panic / 黑屏
- **如何立即回到 Windows**：
  1. 长按主机电源键 5 秒强制关机，再开机连按 **`F11`** 调出铭瑄 B760M D5 UEFI 启动菜单。
  2. 选择 **`Windows Boot Manager (WD_BLACK SN850X 2000GB)`** 回车。
  3. 由于 Windows 主盘与 EFI 分区全程未被修改，您将 100% 正常进入 Windows 10 IoT LTSC 2024。
- **如何修复或回退 macOS 启动**：
  1. 插入保留有已知良好 EFI 备份的恢复 U 盘。
  2. 开机按 `F11` 选择从 U 盘启动 OpenCore。
  3. 在 OpenCore 菜单中可按 `Space`（空格键）选择 **`Reset NVRAM`**，或引导进入 `Recovery` 终端，挂载 `INTEL SSDPEKKF256G8L` 的 `EFI` 分区并回退 `config.plist` / 禁用实验性 Kext。

## 2. 恢复场景二：BIOS 更新后启动项顺序重置
- 铭瑄主板更新 BIOS 或 Clear CMOS 后，通常会将 `Windows Boot Manager` 自动恢复为第一启动项。
- 只需在 BIOS `Boot` 页面重新调整 UEFI Hard Disk Drive BBS Priorities，或日常使用 `F11` 快捷启动菜单切换即可，无需重装任何系统。
