# 存储设备与分区隔离清单 (Storage Inventory)

- **核查日期**：2026-10-26
- **核查方式**：`HKLM:\SYSTEM\CurrentControlSet\Services\disk\Enum`、`DEVICEMAP\Scsi`、`STORAGE\Volume`、`MountedDevices`、`mountvol`、`.NET DriveInfo`
- **证据等级**：`VERIFIED_REAL_HARDWARE`（非管理员沙箱只读枚举；不依赖易变的 Windows `Disk 0 / Disk 1` 编号作为唯一身份）

---

## 1. 物理磁盘硬件身份矩阵

| 角色定位 | 物理型号 | 控制器 PCI ID 与拓扑 | 硬件唯一标识 (脱敏 EUI/Serial) | 容量与状态 | 操作权限边界 |
|---|---|---|---|---|---|
| **Windows 主系统盘（严禁触碰）** | `WD_BLACK SN850X 2000GB` (固件 `61WD`) | `PCI\VEN_15B7&DEV_5030&SUBSYS_503015B7&REV_01` (`Bus 4, Dev 0, Func 0`，挂于 CPU PEG60 `(0,6,0)`) | `E823_8FA6_BF53_0001_001B_448B_...` (Instance `5&2ca6935c&0&000000`) | 2000 GB (2 TB) NVMe，Started | **只读保护 (NEVER TOUCH)**：禁止格式化、禁止改分区、禁止动 EFI/BCD |
| **macOS 目标安装盘（待 Gate C 审批）** | `INTEL SSDPEKKF256G8L` (固件 `L14P`，Intel Pro 7600p 256GB) | `PCI\VEN_8086&DEV_F1A6&SUBSYS_390B8086&REV_03` (`Bus 6, Dev 0, Func 0`，挂于 PCH RP `(0,28,4)`) | `5CD2_E42A_81A5_634C.` (Instance `5&5dd4085&0&000000`) | 256 GB NVMe，Started | **需 Gate C 显式批准后**方可清盘或调整分区；当前保持 100% 只读 |
| **可移动 USB 存储设备** | `Generic Masstorage USB Device` (Rev 1.00) | `USB\VID_8087&PID_1024&MI_00\8&1a614e85&0&0000` | Instance `9&b61d959&0&20170726905923&0` | 挂载为 `E:\` (当前未就绪/无介质或读卡器空置) | **需 Gate B 显式批准后**方可写入安装介质 |

---

## 2. 分区与卷拓扑分析（基于 `STORAGE\Volume` 字节偏移与 `MountedDevices`）

### 2.1 Windows 主盘：`WD_BLACK SN850X 2000GB` (Disk GUID 组 `{ed673af3-9631-11f1-bce3-806e6f6e6963}`)

通过 `STORAGE\Volume` 实例的起始字节偏移量 (`#OffsetHex`) 与 `.NET DriveInfo` 精确还原分区结构：

| 序号 | 起始字节偏移 (Hex / 换算) | 估算容量 | GPT 分区 GUID / 挂载点 | 分区用途判定 | 保护级别 |
|---|---|---|---|---|---|
| Partition 1 | `0x0000000000100000` (1 MiB) | ~100 MiB (`0x6400000`) | 无盘符（ESP） | **Windows EFI System Partition (ESP)** | **最高级保护（严禁写入 OpenCore 或修改 Bootmgfw.efi）** |
| Partition 2 | `0x0000000006500000` (101 MiB) | ~16 MiB (`0x1000000`) | MSR (Microsoft Reserved) | Windows MSR 保留分区 | **最高级保护** |
| Partition 3 | `0x0000000007500000` (117 MiB) | `429,504,065,536 B` (400 GiB) | `C:\` (`7b059bb9-8fab-4d46-b9a6-3eb5cf774900`) | **Windows 10 IoT Enterprise LTSC 2024 主系统分区 (NTFS)** | **最高级保护** |
| Partition 4 | `0x0000006407C00000` (~400.12 GiB) | `1,569,809,494,016 B` (~1462 GiB) | `D:\` (`5b61685b-2b46-4888-8f33-a0929180f04a`) | **Windows 数据与开发工作区分区 (NTFS)** | **工作区授权目录外只读保护** |
| Partition 5 | `0x000001D187C00000` (~1862.12 GiB) | ~800 MiB | 无盘符（WinRE） | **Windows Recovery Environment (恢复分区)** | **最高级保护** |

---

### 2.2 macOS 目标盘：`INTEL SSDPEKKF256G8L` 256GB (Disk GUID 组 `{ed673af6-9631-11f1-bce3-806e6f6e6963}`)

通过 `STORAGE\Volume` 实例确认该 256GB 硬盘当前存在 **旧分区（疑似历史 EFI + Linux 分区）**：

| 序号 | 起始字节偏移 (Hex / 换算) | 估算容量 | 当前 Windows 挂载状态 | 分区用途判定 | 处理方案建议 |
|---|---|---|---|---|---|
| Partition 1 | `0x0000000000100000` (1 MiB) | ~1075 MiB (~1.05 GiB) | 未分配盘符 (`*** NO MOUNT POINTS ***`) | **旧 EFI / `/boot` 分区**（典型 Linux 1GiB boot/EFI 大小） | 见下方方案 A / 方案 B |
| Partition 2 | `0x0000000043400000` (~1076 MiB) | ~237.4 GiB (剩余全盘空间) | 未分配盘符（Windows 不识别 ext4/btrfs/LVM 文件系统或仅保留在 Volume 枚举中） | **旧 Linux 根分区 / 数据分区** | 见下方方案 A / 方案 B |

> **历史盘符记录提示**：`HKLM:\SYSTEM\MountedDevices` 中还记录了 `\DosDevices\F:` (`7078bdc2-1d95-4396-9ec6-9cc857460378`) 与 `\DosDevices\H:` (`6731d419-84d7-41d4-969b-fa375e1a2ded`)，当前均未挂载，可能对应历史分区或外置移动硬盘。

---

## 3. 目标 256GB SSD (`INTEL SSDPEKKF256G8L`) 的两套分区处置方案

根据项目规范第三章 3.5 与第十一章 11.2，由于检测到 `INTEL SSDPEKKF256G8L` 上存在 1.05 GiB + 237.4 GiB 的旧分区（疑似历史 Linux 系统），提供以下两套方案供用户在 **Gate C** 阶段抉择：

### 方案 A（推荐）：全盘清除并重建独立 GPT + 200MB/300MB EFI + 单一 APFS 容器
- **适用前提**：用户确认 `INTEL SSDPEKKF256G8L` (256GB) 上的旧 Linux / EFI 分区无任何需要保留的数据（或已完成备份）。
- **优势**：
  1. 256GB 容量对于 macOS 26 Tahoe + Xcode / 开发缓存较为紧凑，全盘分配给 APFS（约 255GB 可用）可避免空间捉襟见肘。
  2. 彻底清除旧 Linux GRUB / systemd-boot 残留，确保 macOS SSD 的 EFI 分区纯粹只运行 OpenCore 1.0.8。
- **目标盘布局**：
  - `diskX` (`INTEL SSDPEKKF256G8L`, PCI `8086:F1A6` @ Bus 6)
    - `diskXs1`: `EFI` (FAT32, 200 MiB ~ 300 MiB) — 存放独立 OpenCore 引导器
    - `diskXs2`: `Apple_APFS` (~238 GiB) — 包含 `macOS Tahoe - Data`、`macOS Tahoe`、`Preboot`、`Recovery`、`VM`

### 方案 B（保留旧 Linux）：无损缩小旧 Linux 分区，双系统共享第二盘或三系统并存
- **适用前提**：旧 Linux 分区中仍有重要数据或仍需启动 Linux。
- **操作步骤**：使用 Linux Live USB (`gparted`) 将 Partition 2 (`0x43400000` 起) 缩小至 60–80 GiB，腾出 160+ GiB 未分配空间新建 `Apple_APFS` 分区，并在原 1.05 GiB EFI 分区中与 OpenCore 共存。
- **风险与缺点**：256GB 拆分后 macOS 可用空间不足 160GB，且 Linux 与 OpenCore 共享同一个 ESP 不如独占 ESP 干净。

**当前状态**：未获得 Gate C 授权前，不对 `INTEL SSDPEKKF256G8L` 执行任何读写或分区修改。
