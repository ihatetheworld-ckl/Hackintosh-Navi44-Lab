# PCI 与总线设备全量清单 (PCI Inventory)

- **核查日期**：2026-10-26
- **核查方式**：`HKLM:\SYSTEM\CurrentControlSet\Enum\PCI` 与 `pnputil /enum-devices /connected`
- **证据等级**：`VERIFIED_REAL_HARDWARE`

| BDF (Bus,Dev,Func) | Vendor:Device | Subsystem | Rev | Windows 设备描述 | 芯片 / 作用说明 | macOS 26 适配策略 |
|---|---|---|---|---|---|---|
| `(0,0,0)` | `8086:4648` | `6688:0760` | `02` | Intel Host Bridge/DRAM Registers - 4648 | Alder Lake 6P+4E Host Bridge | 原生识别 |
| `(0,1,0)` | `8086:460D` | `6688:0760` | `02` | Intel PEG10 - 460D | CPU PCIe 5.0 x16 Root Port (连接 RX 9060 XT) | 原生 PCIe Bridge |
| `(0,6,0)` | `8086:464D` | `0000:0000` | `02` | Intel PEG60 - 464D | CPU PCIe 4.0 x4 Root Port (连接 Bus 4 WD SN850X NVMe) | 原生 PCIe Bridge |
| `(0,8,0)` | `8086:464F` | `6688:0760` | `02` | Intel GNA Scoring Accelerator module | 高斯神经加速器 | macOS 无需驱动，静默忽略 |
| `(0,10,0)` | `8086:467D` | `0000:0000` | `01` | Intel Platform Monitoring Technology Driver | 平台遥测 | macOS 无需驱动，静默忽略 |
| `(0,20,0)` | `8086:7A60` | `6688:0760` | `11` | Intel USB 3.20 eXtensible Host Controller | B760 原生 XHCI 控制器 | 原生驱动 + `USBToolBox.kext` + `UTBMap.kext` |
| `(0,20,2)` | `8086:7A27` | `0000:0000` | `11` | PCI standard RAM Controller | PCH Shared SRAM | 无需驱动 |
| `(0,20,3)` | `8086:7A70` | `8086:0244` | `11` | Intel Wi-Fi 6 AX101 | CNVi 1x1 Wi-Fi 6 无线网卡 | 需验证 `itlwm.kext` (HeliPort) 或 Tahoe 版 `AirportItlwm` 对 `7A70` CNVi 的支持 |
| `(0,21,0..3)` | `8086:7A4C..7A4F` | `6688:0760` | `11` | PCI Device (Serial IO I2C #0..#3) | B760 LPSS I2C 控制器 | 台式机无 I2C 触控板，无需加载 `VoodooI2C` |
| `(0,22,0)` | `8086:7A68` | `6688:0760` | `11` | Intel Management Engine Interface #1 | HECI / IMEI | 原生识别 |
| `(0,23,0)` | `8086:7A62` | `6688:0760` | `11` | Standard SATA AHCI Controller | B760 SATA AHCI 控制器 | 原生 `AppleAHCIPort` 支持 |
| `(0,25,0..1)` | `8086:7A7C..7A7D` | `6688:0760` | `11` | PCI Device (Serial IO I2C #4..#5) | B760 LPSS I2C 控制器 | 无需驱动 |
| `(0,28,0)` | `8086:7A38` | `6688:0760` | `11` | PCI-to-PCI Bridge | PCH Root Port #1 (连接 Bus 5 ASMedia USB 控制器) | 原生 PCIe Bridge |
| `(0,28,4)` | `8086:7A3C` | `6688:0760` | `11` | PCI-to-PCI Bridge | PCH Root Port #5 (连接 Bus 6 Intel 256GB NVMe) | 原生 PCIe Bridge |
| `(0,29,0)` | `8086:7A36` | `6688:0760` | `11` | PCI-to-PCI Bridge | PCH Root Port #9 (连接 Bus 7 Realtek RTL8125 网卡) | 原生 PCIe Bridge |
| `(0,30,0)` | `8086:7A28` | `6688:0760` | `11` | PCI Simple Communications Controller | Serial IO UART #0 | 无需驱动 |
| `(0,30,3)` | `8086:7A2B` | `0000:0000` | `11` | PCI Device | Serial IO GSPI #1 | 无需驱动 |
| `(0,31,0)` | `8086:7A06` | `6688:0760` | `11` | PCI standard ISA bridge | B760 LPC / eSPI Controller | 挂载 `SSDT-EC` / `SSDT-RTCAWAC` |
| `(0,31,3)` | `8086:7A50` | `10EC:0897` | `11` | High Definition Audio Controller | B760 HDA 控制器 (Codec: ALC897) | Tahoe 移除 `AppleHDA`；优先 USB 声卡或研究 AppleHDA 恢复方案 |
| `(0,31,4)` | `8086:7A23` | `6688:0760` | `11` | SM Bus Controller | PCH SMBus | 原生识别 |
| `(0,31,5)` | `8086:7A24` | `6688:0760` | `11` | PCI Device (SPI Controller) | PCH SPI Flash Controller | 无需驱动 |
| `(1,0,0)` | `1002:1478` | `1458:1478` | `25` | AMD PCI Express Upstream Switch Port | Navi 44 PCIe Upstream Bridge | 原生 PCIe Bridge |
| `(2,0,0)` | `1002:1479` | `1002:1479` | `25` | AMD PCI Express Downstream Switch Port | Navi 44 PCIe Downstream Bridge | 原生 PCIe Bridge |
| `(3,0,0)` | `1002:7590` | `1458:2438` | `C0` | **AMD Radeon RX 9060 XT** | **Navi 44 / RDNA4 / gfx1200 GPU** | **核心攻关对象**：UEFI GOP 帧缓冲过渡 → `AMDRadeonRDNA4-Navi44` / `Cobalt64` 适配 |
| `(3,0,1)` | `1002:AB40` | `1002:AB40` | `00` | High Definition Audio Bus | Navi 44 HDMI/DP 音频控制器 | 依赖 GPU Display Engine / DCN 音频通道与 HDA 支持 |
| `(4,0,0)` | `15B7:5030` | `15B7:5030` | `01` | Standard NVM Express Controller | **WD_BLACK SN850X 2000GB** (Windows 主系统盘控制器) | **绝对只读保护对象**；macOS 原生 `IONVMeFamily` 识别，可通过 fstab/DeviceProperties 屏蔽自动挂载写操作 |
| `(5,0,0)` | `1B21:2142` | `1B21:2142` | `00` | USB xHCI Compliant Host Controller | ASMedia ASM2142/3142 USB 3.1 控制器 | 原生 `AppleUSBXHCI` 支持 |
| `(6,0,0)` | `8086:F1A6` | `8086:390B` | `03` | Standard NVM Express Controller | **INTEL SSDPEKKF256G8L (256GB)** (macOS 目标安装盘控制器) | Intel Pro 7600p/760p 控制器，macOS 原生 `IONVMeFamily` 完美支持 |
| `(7,0,0)` | `10EC:8125` | `10EC:0123` | `05` | Realtek Gaming 2.5GbE Family Controller | Realtek RTL8125B 2.5G 有线网卡 | `LucyRTL8125Ethernet.kext` (v1.2.2) 稳定支持 |
