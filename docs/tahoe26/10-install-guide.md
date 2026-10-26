# 10 — macOS 26 Tahoe 从零安装全流程手册 (Step-by-Step Install Guide — Section 11.4)

> **前置门禁**：必须先完成 M6（在真实 Mac 上构建/准备 `.aml` 与官方 Kext 二进制）并获得您的 **Gate B（U 盘制作）** 与 **Gate C（`INTEL SSDPEKKF256G8L` 256GB 写盘授权）**。

---

## 阶段一：安装前准备与 Windows 隔离
1. **核对 BIOS 设置**（铭瑄 MS-Terminator B760M D5 BIOS `E1.5D`，开机按 `Del`）：
   - `Secure Boot`：已实测为 `Disabled` (`0`)，保持关闭。
   - `Above 4G Decoding`：`Enabled`；`Re-Size BAR Support`：`Enabled`（或测试时按需切换）。
   - `XHCI Hand-off`：`Enabled`。
   - `CFG Lock`：若 BIOS 中有该项则设为 `Disabled`（候选 `config.plist` 已开启 `AppleXcpmCfgLock = true` 双保险）。
   - `VT-d`：保持 `Enabled`（候选配置兼容 IOMMU）。
2. **执行 Windows 主盘隔离**（二选一）：
   - **物理隔离（推荐）**：关机断电，取下 M.2 Slot 1 上的 `WD_BLACK SN850X 2000GB`。
   - **ACPI 逻辑隔离（免拆机）**：在 U 盘 `EFI/OC/config.plist` 中将 `SSDT-NVME-PROTECT.aml` 设为 `Enabled = true`，使 Darwin 内核完全屏蔽 `PciRoot(0x0)/Pci(0x6,0x0)/Pci(0x0,0x0)` (`15B7:5030`)。

## 阶段二：U 盘启动与磁盘格式化
3. 插入制作好的 macOS 26 Tahoe 安装 U 盘，开机连按 **`F11`** 调出铭瑄主板 UEFI 启动菜单，选择 **`UEFI: <您的 U 盘名称>, Partition 1`**。
4. 进入 OpenCore 1.0.8 菜单，选择 **`Install macOS Tahoe`** 回车。
5. 观察 `-v` 啰嗦模式滚动日志，依靠 RX 9060 XT 的 **UEFI GOP Framebuffer** 进入 macOS 26 Recovery 安装界面。
6. 打开 **磁盘工具 (Disk Utility)** → 点击左上角 `显示 (View)` → 选择 **显示所有设备 (Show All Devices)**。
7. **严格核对磁盘身份**：
   - 确认选中 **`INTEL SSDPEKKF256G8L Media`**（容量约 `256.06 GB`，PCI 路径 `PciRoot(0x0)/Pci(0x1C,0x4)/Pci(0x0,0x0)`）。
   - 若您选择了**全盘清除方案**（Gate C 批准后）：点击 `抹掉 (Erase)` → 名称填 `macOS Tahoe`，格式选 `APFS`，方案选 `GUID 分区图 (GUID Partition Map)` → 确认抹掉。

## 阶段三：系统安装与多次重启引导项选择
8. 退出磁盘工具，点击 **安装 macOS Tahoe (Install macOS Tahoe)**，选择目标卷 `macOS Tahoe`。
9. **第一次自动重启（约 10–15 分钟后）**：
   - 开机按 `F11` 从 U 盘启动 OpenCore，此时 OpenCore 菜单会出现 **`macOS Installer`** 启动项（OpenCore 会自动高亮它），选择 **`macOS Installer`** 继续第二阶段安装。
10. **第二次/第三次自动重启**：
    - 只要菜单中仍存在 `macOS Installer`，继续从 U 盘引导并选择 `macOS Installer`。
    - 当 `macOS Installer` 消失、变为 **`macOS Tahoe`** 时，选择 **`macOS Tahoe`** 进入国家/地区与账户初始化向导。

## 阶段四：独立 EFI 部署与双系统联合验证
11. 进入 macOS 26 桌面后，先通过 U 盘稳定运行，打开终端执行 `diskutil list`，再次确认 `INTEL SSDPEKKF256G8L` 的 `EFI` 分区标识符（例如 `disk0s1` 或 `disk1s1`）。
12. 挂载 `INTEL SSDPEKKF256G8L` 的 `EFI` 分区，将 U 盘中的 `EFI/BOOT` 与 `EFI/OC` 复制到该 SSD 的 `EFI` 分区中（若此前启用了 `SSDT-NVME-PROTECT.aml`，可在此决定是否保留隐藏 Windows 盘或恢复只读可见）。
13. 拔掉安装 U 盘，重启电脑：
    - 测试仅靠 `INTEL SSDPEKKF256G8L` 能否直接引导进入 OpenCore 与 macOS 26 Tahoe。
    - 重启按 `F11` 选择 `Windows Boot Manager`，验证 Windows 10 IoT LTSC 2024 能否 100% 正常独立启动。
