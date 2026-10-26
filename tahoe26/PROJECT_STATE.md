# PROJECT TAHOE26 — 持久化项目状态文件 (PROJECT_STATE)

- **最后更新时间**：2026-10-26T15:10:00+08:00
- **工作区路径**：`D:\AntigravityWorkSpace\黑苹果研究\Hackintosh-Navi44-Lab`
- **原始参考工作区（含便携工具链与上游克隆，只读引用）**：`D:\CodexWorkSpace\黑苹果研究\Hackintosh-Navi44-Lab`
- **当前 Git 分支**：`tahoe26-dev`（基于 `main` `6b088ba` 创建，已获 Gate E 授权推送远端）
- **当前总体状态**：**`PARTIAL` (M0–M5 & M7 离线研发完成，非物理拆机双层 NVMe 隔离已默认启用，macOS 27 制盘与 M6 原生验证一键脚本已推送，等待用户在 Mac 上执行 M6 与制作安装盘)**

---

## 1. 已核实的真实主机硬件基线 (`VERIFIED_REAL_HARDWARE`)

| 组件 | 实测型号与硬件标识 | 状态与关键属性 |
|---|---|---|
| **CPU** | `12th Gen Intel(R) Core(TM) i5-12600KF` (`0x069702`) | 6 P-Cores + 4 E-Cores (16 Logical Processors)，**无核显** |
| **主板 / BIOS** | `Maxsun MS-Terminator B760M D5` / AMI BIOS `E1.5D` (`08/13/2024`) | UEFI 模式，`UEFISecureBootEnabled = 0` (已关闭)，TPM `600.18.30.2255` 已启用 |
| **内存** | `32 GB DDR5` (`34,186,244,096 bytes`) | 双通道 DDR5 |
| **GPU** | `Gigabyte AMD Radeon RX 9060 XT 16GB` (`PCI\VEN_1002&DEV_7590&SUBSYS_24381458&REV_C0`) | Navi 44 / RDNA4 / `gfx1200`，位于 Bus 0 `(0,1,0)` → Bus 1 `1002:1478` → Bus 2 `1002:1479` → Bus 3 `(3,0,0)`；VBIOS `113-R906XGOI-F1` |
| **显示器** | `HKC2410` / `G24H2D` (`DISPLAY\HKC2410\7&d0c0685&0&UID260`) | 实测 384B EDID：Block 0 `1440p60` (`241.7 MHz`)、Block 1 CTA `1440p120`/`1440p144`、Block 2 DisplayID v1.2 Tag `0x03` `2560x1440@180Hz` (`725.10 MHz`) |
| **有线网卡** | `Realtek Gaming 2.5GbE RTL8125` (`PCI\VEN_10EC&DEV_8125&SUBSYS_012310EC&REV_05`) | Bus 7, Dev 0, Func 0 (`LucyRTL8125Ethernet.kext` v1.2.2) |
| **无线 / 蓝牙** | `Intel Wi-Fi 6 AX101` (`8086:7A70` @ `(0,20,3)`) + `Intel Bluetooth` (`USB\VID_8087&PID_0026` @ `HS14`) | CNVi 1x1 Wi-Fi + 内置 USB 蓝牙 |
| **音频** | 板载 `Realtek ALC897` (`10EC:0897`) + GPU `1002:AB40` + 外接 USB `Philips SPA3609 USB` / `TSP207` (`3769:B020`) | Tahoe 移除 `AppleHDA`；外接 USB 音频免驱直接可用 |
| **Windows 主盘** | `WD_BLACK SN850X 2000GB` (`PCI\VEN_15B7&DEV_5030` @ Bus 4, Serial `E823_8FA6_...`) | **绝对只读保护对象（不物理拆下，采用 OpenCore ACPI + PCI DeviceProperties 双重软件屏蔽）** |
| **macOS 目标盘** | `INTEL SSDPEKKF256G8L` 256GB (`PCI\VEN_8086&DEV_F1A6` @ Bus 6, Serial `5CD2_E42A_81A5_634C.`) | 原为旧 Ubuntu 系统（1.05GiB + 237.4GiB），**用户已批准在确保不影响 Windows 盘的前提下全盘清空安装 macOS 26** |
| **辅助 Apple Mac** | 真实 Apple Mac（运行 **macOS 27**） | 用于执行 M6 原生 Mach-O 编译验证、下载 macOS 26 Tahoe 完整安装器并制作离线安装 U 盘 |

---

## 2. 已完成阶段与最近真实测试证据 (`VERIFIED_HOST_ONLY`)

1. **Navi44 驱动核心研发 (`development/AMDRadeonRDNA4-Navi44`)**：
   - 新增 VESA DisplayID v1.2/v1.3/v2.0 (`0x70`) 扩展块与 Type I (`0x03`/`0x01`) / Type VII (`0x22`) 20-byte 详细时序解析，完整覆盖本机 `HKC2410` (`G24H2D`) 显示器的 `2560x1440@180Hz` (`725,100 kHz`) 与 `734,400 kHz` 时序及 DP HBR3 带宽预检。
   - 新增 `NaviDisplay::boardDiagnostics` 封装 AtomBIOS `FirmwareInfo3` 与 `GpioPinLut` 只读诊断。
   - 新增 `N44Q 1.0` (128B) → `CobaltQueryProjection` (192B `n48n_info` 兼容布局) 显式安全投影与解码校验。
   - **真实编译与测试结果**（编译器：LLVM-MinGW `20261006` Clang `23.1.3`，Python `3.12.13`）：
     - Python 测试：4 个测试文件全部 `PASS`
     - C++ 单元测试：`m65_unit = 34 PASS`、`m7_unit = 31 PASS`、`m8_unit = 108 PASS`（共 **`173 PASS, 0 FAIL`**）
     - 有界变异测试：`M8_FUZZ = 2400 PASS`、`M8_QUERY_FUZZ = 800 PASS`、`M9_EXT_FUZZ = 800 PASS`（共 **`4000 组变异，invariants=PASS`**）
     - 静态分析：`clang++ --analyze` **零警告 (`exit=0`)**
2. **OpenCore 1.0.8 候选工程 (`tahoe26/opencore/`)**：
   - 针对用户“不物理拆下 Windows 主盘”的要求，在 `config.plist` 中默认启用**双层免拆机隔离保护**：
     - 第 1 层（PCI 属性级）：在 `DeviceProperties -> Add -> PciRoot(0x0)/Pci(0x6,0x0)/Pci(0x0,0x0)` 注入 `class-code = <FFFFFFFF>` 与 `IOName = "#disabled-nvme"`，阻止 `IONVMeFamily.kext` 绑定 Windows 2TB 主盘。
     - 第 2 层（ACPI 级）：默认启用 `SSDT-NVME-PROTECT.aml`（仅在 `_OSI("Darwin")` 下令 `\_SB.PC00.PEG1.PEGP._STA` 返回 `0x00`）。
   - 离线验证脚本 `validate_opencore_candidate.py`：**`13 / 13 PASS`**。

---

## 3. 分级授权门禁状态 (Gate Status)

| 门禁 | 范围 | 当前授权状态 |
|---|---|---|
| **Gate A** | 离线研究、只读硬件普查、源码开发、Windows Host 编译与测试、候选 EFI 生成 | **ACTIVE (已获授权并持续执行)** |
| **Gate B** | 在真实 Mac (macOS 27) 上制作 macOS 26 Tahoe 离线安装 U 盘并写入 EFI | **READY FOR USER EXECUTION (已提供完整命令与自动化组装脚本 `assemble_efi_on_mac.py`)** |
| **Gate C** | 目标 SSD (`INTEL SSDPEKKF256G8L` 256GB) 清空旧 Ubuntu 并安装 macOS 26 Tahoe | **APPROVED BY USER (前提：Recovery 下先通过 `diskutil list` 核验 Windows 2TB 盘已隐藏不可见)** |
| **Gate D** | 在真机 macOS 上加载实验性 `AMDRadeonRDNA4-Navi44.kext`、访问 GPU 寄存器/ROM/固件 | **LOCKED (等待基础系统安装完成后单独审批)** |
| **Gate E** | 推送 `tahoe26-dev` 分支至 GitHub 远程仓库 (`ihatetheworld-ckl/Hackintosh-Navi44-Lab`) | **APPROVED BY USER (已获批执行推送)** |
