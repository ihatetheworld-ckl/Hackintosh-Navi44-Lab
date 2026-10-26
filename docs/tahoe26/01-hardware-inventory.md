# 01 — 硬件普查汇总 (Hardware Inventory Summary)

完整硬件、PCI 拓扑与存储分区矩阵已生成并持久化于：
- [hardware-inventory.md](../../tahoe26/hardware/hardware-inventory.md)
- [pci-inventory.md](../../tahoe26/hardware/pci-inventory.md)
- [storage-inventory.md](../../tahoe26/hardware/storage-inventory.md)

## 核心实测摘要 (`VERIFIED_REAL_HARDWARE`)
- **CPU**：`12th Gen Intel(R) Core(TM) i5-12600KF` (`0x069702`, 6P+4E / 16 线程，无核显)
- **主板**：`Maxsun MS-Terminator B760M D5` (铭瑄终结者 B760M D5，BIOS `E1.5D` `08/13/2024`，Secure Boot = `0` 已关闭，TPM `600.18.30.2255` 已启用)
- **内存**：32 GB DDR5 (`34,186,244,096 B`)
- **独立显卡**：`Gigabyte AMD Radeon RX 9060 XT 16GB` (`PCI\VEN_1002&DEV_7590&SUBSYS_24381458&REV_C0`，位于 Bus 0 `(0,1,0)` → Bus 1 `1002:1478` → Bus 2 `1002:1479` → Bus 3 `(3,0,0)`；VBIOS 字符串 `113-R906XGOI-F1`)
- **显示器**：`HKC2410` (支持 1440p 高刷 DisplayID 模式)
- **有线网卡**：`Realtek Gaming 2.5GbE RTL8125` (`PCI\VEN_10EC&DEV_8125&SUBSYS_012310EC&REV_05` @ Bus 7)
- **无线网卡与蓝牙**：`Intel Wi-Fi 6 AX101` (`PCI\VEN_8086&DEV_7A70&SUBSYS_02448086&REV_11` @ `(0,20,3)`) + `Intel Wireless Bluetooth` (`USB\VID_8087&PID_0026` @ `HS14`)
- **音频**：板载 `Realtek ALC897` (`10EC:0897` @ HDA `8086:7A50`) + GPU HDMI/DP Audio (`1002:AB40`) + 外接 USB Audio (`TSP207` `3769:B020` / `Philips SPA3609 USB`)
- **Windows 主系统盘（严禁触碰）**：`WD_BLACK SN850X 2000GB` (`PCI\VEN_15B7&DEV_5030` @ Bus 4，含 100MB ESP + 16MB MSR + 400GB `C:` + 1462GB `D:` + 800MB WinRE)
- **macOS 目标安装盘（待 Gate C 批准）**：`INTEL SSDPEKKF256G8L` 256GB (`PCI\VEN_8086&DEV_F1A6` @ Bus 6，当前含约 1.05GiB 旧 EFI/boot 分区 + 237.4GiB 旧 Linux 分区)
