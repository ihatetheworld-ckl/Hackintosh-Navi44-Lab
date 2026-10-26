# 04 — Alder Lake CPU 与 Maxsun B760M D5 ACPI 适配 (CPU & ACPI)

## 1. CPU 适配设计 (`i5-12600KF`)
- **CPUID 仿冒**：在 `config.plist -> Kernel -> Emulate` 中设置：
  - `Cpuid1Data`: `55 06 0A 00 00 00 00 00 00 00 00 00 00 00 00 00` (Comet Lake `0x0A0655`)
  - `Cpuid1Mask`: `FF FF FF FF 00 00 00 00 00 00 00 00 00 00 00 00`
- **大小核 (6P+4E) 拓扑策略**：
  - **主方案（保留 E-Core，满血 10 核 16 线程）**：启用 `ProvideCurrentCpuInfo = true` + `CpuTopologyRebuild.kext`，将 6 个 P-Core (12 线程) 与 4 个 E-Core (4 线程) 均正确映射给 XNU 调度器，无性能损失。
  - **备选方案（仅在特定应用受异构核心影响时使用）**：若关闭 4 个 E-Core，多核性能约损失 20%–25%，当前无需关闭。

## 2. 本机定制 ACPI 表 (`tahoe26/opencore/acpi/`)
基于注册表 `HKLM:\HARDWARE\ACPI` 实测表签名（根桥 `\_SB.PC00`、处理器 `\_SB.PR00`、LPC `\_SB.PC00.LPCB`）：
1. [`SSDT-PLUG-ALT.dsl`](../../tahoe26/opencore/acpi/SSDT-PLUG-ALT.dsl)：在 `\_SB.PR00` 注入 `plugin-type = 1` 激活 XCPM。
2. [`SSDT-EC-USBX.dsl`](../../tahoe26/opencore/acpi/SSDT-EC-USBX.dsl)：在 `\_SB.PC00.LPCB` 下创建 `EC` (`ACID0001`，仅 `_OSI("Darwin")` 生效)，并在 `\_SB.USBX` 注入 USB 供电电流属性。
3. [`SSDT-RTCAWAC.dsl`](../../tahoe26/opencore/acpi/SSDT-RTCAWAC.dsl)：在 `_OSI("Darwin")` 下置 `STAS = 1`，禁用 B760 AWAC 时钟并启用传统 RTC。
4. [`SSDT-NVME-PROTECT.dsl`](../../tahoe26/opencore/acpi/SSDT-NVME-PROTECT.dsl)：可选安装期保护表，仅在 `_OSI("Darwin")` 下将 `\_SB.PC00.PEG1.PEGP` (`WD_BLACK SN850X 2000GB`) 标记为 `#disabled-nvme`，防止 macOS 安装器误触 Windows 主盘。
