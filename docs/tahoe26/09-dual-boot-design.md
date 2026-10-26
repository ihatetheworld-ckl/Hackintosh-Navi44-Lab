# 09 — 双硬盘双独立 EFI 启动架构设计 (Dual-Boot Isolation Design — Chapter 2 & 11)

详见 [windows-protection-baseline.md](../../tahoe26/hardware/windows-protection-baseline.md) 与 [storage-inventory.md](../../tahoe26/hardware/storage-inventory.md)。

## 1. 双盘物理与逻辑完全解耦表

| 属性 | Windows 主盘（只读保护） | macOS 目标盘（待 Gate C 审批） |
|---|---|---|
| **物理型号** | `WD_BLACK SN850X 2000GB` | `INTEL SSDPEKKF256G8L` (256GB) |
| **NVMe 控制器 PCI ID** | `15B7:5030` (Rev `01`) | `8086:F1A6` (Rev `03`) |
| **PCIe 拓扑位置** | Bus 4, Dev 0, Func 0 (CPU PEG60 `(0,6,0)`) | Bus 6, Dev 0, Func 0 (PCH RP `(0,28,4)`) |
| **脱敏硬件序列号** | `E823_8FA6_BF53_0001_...` | `5CD2_E42A_81A5_634C.` |
| **EFI 系统分区 (ESP)** | 独立 100 MB ESP (`offset 1 MiB`)，仅含 `Microsoft/Boot` | 独立 300 MB ESP，仅含 `EFI/BOOT` + `EFI/OC` (OpenCore 1.0.8) |
| **系统引导方式** | 主板默认启动项 `Windows Boot Manager` | 主板 `F11` 启动菜单或将 `UEFI OS (INTEL SSDPEKKF256G8L)` 设为第一启动项 |

## 2. 六项独立性验收标准 (Section 2.2)
1. `WD_BLACK SN850X 2000GB` 单独存在时，Windows 10 IoT LTSC 2024 正常冷启动。
2. `INTEL SSDPEKKF256G8L` 单独存在时，OpenCore 1.0.8 与 macOS 26 Tahoe 独立冷启动。
3. 两块 NVMe 同时连接时，可通过铭瑄 B760M D5 主板 UEFI Boot Menu (`F11`) 分别独立选择启动。
4. 拔除 `INTEL SSDPEKKF256G8L` 后，Windows 启动不受任何影响。
5. macOS 26 运行完全不依赖 `WD_BLACK SN850X` 上的任何文件。
6. 即使 macOS 安装或 GPU 实验失败，只需按 `F11` 选择 `Windows Boot Manager` 即可 100% 无损回到 Windows。
