# PROJECT TAHOE26 — 本轮产出与下一步行动清单 (NEXT_ACTIONS)

## 1. 本轮实际完成内容 (Round 1 Summary)

1. **M0 项目接管与环境审查**：
   - 核实工作区 `D:\AntigravityWorkSpace\黑苹果研究\Hackintosh-Navi44-Lab` 与原工作区 `D:\CodexWorkSpace\黑苹果研究\Hackintosh-Navi44-Lab`。
   - 创建独立 Git 分支 `tahoe26-dev`，完整保留 M6–M8.5 历史提交、测试与 BSD/MIT/Apache 许可证。
2. **M1 主机硬件只读全面普查**：
   - 通过注册表、`pnputil`、Win32 API 与 `.NET DriveInfo` 精确核实 `i5-12600KF`、`Maxsun MS-Terminator B760M D5` (BIOS `E1.5D`, Secure Boot = `0`)、32GB DDR5、`Gigabyte RX 9060 XT 16GB` (`1002:7590`, Subsys `1458:2438`, Rev `C0`, 三层 PCIe Switch 拓扑 `Bus 0->1->2->3`)、`RTL8125` (`10EC:8125`)、`AX101` (`8086:7A70`)、蓝牙 (`8087:0026`)、`ALC897` (`10EC:0897`)、USB 音频 (`Philips SPA3609 USB` / `TSP207`)。
   - 精确区分 Windows 主盘 `WD_BLACK SN850X 2000GB` (`15B7:5030` @ Bus 4) 与 macOS 目标盘 `INTEL SSDPEKKF256G8L` 256GB (`8086:F1A6` @ Bus 6)，并发现目标 256GB SSD 存在两个旧分区（约 1.05GiB + 237.4GiB，疑似旧 Linux）。
3. **M2–M4 上游调研与 OpenCore 1.0.8 候选工程生成**：
   - 核实 2026 年 10 月最新 OpenCore `1.0.8`、Lilu `1.7.2`、VirtualSMC `1.3.8` 对 macOS 26 Tahoe 的支持及 Tahoe 移除 `AppleHDA.kext` 的影响。
   - 编写本机专属 `SSDT-PLUG-ALT.dsl`、`SSDT-EC-USBX.dsl`、`SSDT-RTCAWAC.dsl`、`SSDT-NVME-PROTECT.dsl`（免拆机隐藏 Windows NVMe 防误格保护）、`UTBMap.kext` 与 `config.plist`，并通过 `validate_opencore_candidate.py` 全部 12 项校验。
4. **M5 Navi44 驱动源码开发与离线测试**：
   - 在 `src/edid.hpp/.cpp` 与 `core/display.hpp/.cpp` 中实现 VESA DisplayID v1.3/v2.0 (`0x70`) 扩展块解析，支持 `2560x1440@180Hz` (`734.4 MHz`) 高刷时序与 DP HBR3 链路预算评估。
   - 在 `core/query_candidate.hpp/.cpp` 中实现 `N44Q 1.0` (128B) → `CobaltQueryProjection` (192B `n48n_info` 兼容布局) 的安全字段映射与反向校验。
   - 通过 Clang `23.1.3` 编译、静态分析（0 warning）、`171 PASS` C++ 单元测试与 `4000` 组有界变异测试。

---

## 2. 本轮新增与修改文件清单

### 修改的源码与测试文件
- `development/AMDRadeonRDNA4-Navi44/src/edid.hpp`
- `development/AMDRadeonRDNA4-Navi44/src/edid.cpp`
- `development/AMDRadeonRDNA4-Navi44/core/display.hpp`
- `development/AMDRadeonRDNA4-Navi44/core/display.cpp`
- `development/AMDRadeonRDNA4-Navi44/core/query_candidate.hpp`
- `development/AMDRadeonRDNA4-Navi44/core/query_candidate.cpp`
- `tests/fixtures/m8_display.hpp`
- `tests/unit/m8_unit.cpp`
- `tests/unit/m8_fuzz.cpp`

### 新增的 `tahoe26/` 与 `docs/tahoe26/` 工程文件
- `tahoe26/README.md`, `tahoe26/PROJECT_STATE.md`, `tahoe26/NEXT_ACTIONS.md`
- `tahoe26/hardware/{hardware-inventory,pci-inventory,storage-inventory,compatibility-inventory,windows-protection-baseline}.md`
- `tahoe26/research/navi44-vs-navi48-model.md`
- `tahoe26/opencore/acpi/{SSDT-PLUG-ALT,SSDT-EC-USBX,SSDT-RTCAWAC,SSDT-NVME-PROTECT}.dsl`
- `tahoe26/opencore/EFI/OC/config.plist`
- `tahoe26/opencore/EFI/OC/Kexts/UTBMap.kext/Contents/Info.plist`
- `tahoe26/scripts/{validate_opencore_candidate,run_mac_native_verification}.py`
- `tahoe26/tests/host/opencore-validation-report.json`
- `docs/tahoe26/00-project-overview.md` .. `15-project-progress.md` (全套 16 份工程文档)

---

## 3. 下一步可自动推进的研发任务 (Gate A 范围内)

1. 进一步扩展 `development/AMDRadeonRDNA4-Navi44/core/` 对 AtomBIOS `VramInfo` / `DceInfo` / `GpioPinLut` 数据表的纯 CPU 安全解析封装，为 Gate D 真机读取 Gigabyte RX 9060 XT (`1458:2438`) 连接器路由做准备。
2. 编写针对 `Cobalt64` `mesa-patches/0002` 与 `0007` 的 `gfx1200` 适配候选补丁（移除 `ACD_GB_ADDR_CONFIG_GFX1201` 硬编码阻塞，改为基于 `N44P` / `gfx1200` 动态校验）。
3. 编写 Windows 侧只读采集显示器注册表 EDID（`HKLM:\SYSTEM\CurrentControlSet\Enum\DISPLAY\HKC2410\...\Device Parameters\EDID`）并在离线解析器中验证本机真实 `HKC2410` 显示器描述符的辅助测试。

---

## 4. 需要用户确认的具体授权事项

1. **Apple Mac 原生构建协同（M6）**：
   - 请确认您的真实 Apple Mac 的系统版本、架构（Apple Silicon 还是 Intel）及 Xcode 版本，并确认是否方便在 Mac 上运行 `python3 tahoe26/scripts/run_mac_native_verification.py`（以及用于下载官方 `Install macOS Tahoe.app` 与编译 `.aml`）。
2. **Gate E（可选，用于向您的 Apple Mac 同步代码）**：
   - 是否批准将当前新建的独立分支 `tahoe26-dev` 推送到您的 GitHub 仓库 `ihatetheworld-ckl/Hackintosh-Navi44-Lab`（不触碰 `main` 分支），以便您的 Apple Mac 直接 `git pull` 拉取最新代码与脚本？
3. **Gate C 前置确认（关于第二块硬盘 `INTEL SSDPEKKF256G8L` 256GB）**：
   - 我们检测到该 256GB Intel NVMe (`PCI\VEN_8086&DEV_F1A6` @ Bus 6) 上目前有两个旧分区（约 1.05 GiB + 237.4 GiB，疑似旧 Linux 系统）。请确认上面的旧数据是否已不再需要、允许在后续安装阶段选择**方案 A（全盘抹掉重建独立 EFI + 单一 APFS 容器）**？
4. **Gate B 前置确认（关于安装 U 盘）**：
   - 您准备使用哪个容量的 U 盘制作 macOS 26 Tahoe 安装介质？是否优先在您的真实 Apple Mac 上使用官方 `createinstallmedia` 制作完整离线安装盘（方案 A）？
