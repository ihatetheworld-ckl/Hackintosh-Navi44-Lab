# PROJECT TAHOE26 — 本轮产出与下一步行动清单 (NEXT_ACTIONS)

## 1. 本轮新增完成内容 (Round 2 Summary)

1. **落实免物理拆机 Windows 2TB 主盘双层隔离 (`tahoe26/opencore/EFI/OC/config.plist`)**：
   - 默认启用 `SSDT-NVME-PROTECT.aml` (`Enabled = true`)。
   - 在 `DeviceProperties -> Add -> PciRoot(0x0)/Pci(0x6,0x0)/Pci(0x0,0x0)` 注入 `class-code = <FFFFFFFF>`、`IOName = "#disabled-nvme"`、`name = <2364697361626c65642d6e766d6500>`，确保 macOS 的 `IONVMeFamily.kext` 完全不挂载 `WD_BLACK SN850X 2000GB`，而仅识别 Bus 6 (`PciRoot(0x0)/Pci(0x1C,0x4)/Pci(0x0,0x0)`) 上的 `INTEL SSDPEKKF256G8L` (256GB)。
   - 更新 `tahoe26/scripts/validate_opencore_candidate.py` 并运行验证：**`13 / 13 PASS`**。
2. **适配真实 Mac (macOS 27) 制盘与原生验证自动化脚本**：
   - 更新 `tahoe26/scripts/run_mac_native_verification.py`：支持在 macOS 27 (Apple Silicon 或 Intel) 下通过 `clang++ -target x86_64-apple-macos26.0` 编译验证全部 11 个核心驱动源码与 173 项单元测试，并自动调用 `iasl` 将 4 个 `.dsl` 编译为 `.aml`。
   - 新增 `tahoe26/scripts/assemble_efi_on_mac.py`：在 Mac 上一键校验全部二进制/Kext、自动调用 `macserial -m MacPro7,1` 生成本机独立序列号填入 `EFI_READY/EFI/OC/config.plist`（不污染 Git 仓库）、并调用 `ocvalidate` 做官方结构校验。
   - 更新 `docs/tahoe26/07-native-build.md` 与 `docs/tahoe26/10-install-guide.md`：专门针对 **macOS 27 下载 macOS 26 Tahoe 安装器**（必须显式指定 `--full-installer-version 26.x`）及免拆机安装核验流程编写完整分步指南。
3. **本机真实显示器 `HKC2410` (`G24H2D`) EDID 核查与驱动源码增强**：
   - 从 Windows 注册表只读提取本机 `HKC2410` (`G24H2D`) 384 字节 3-Block EDID，发现其 `2560x1440@180Hz` (`725.10 MHz`) 模式存储于 Block 2 DisplayID v1.2 (`0x12`) 的 Tag `0x03` 数据块中。
   - 更新 `src/edid.cpp` 支持 DisplayID v1.2 Tag `0x03` 详细时序块，新增 `NaviDisplay::boardDiagnostics` 接口，并通过全部 **173 项 C++ 单元测试 + 4000 组变异测试**。
4. **执行用户批准的 Gate E 推送 (`git push -u origin tahoe26-dev`)**。

---

## 2. 用户在真实 Mac (macOS 27) 与目标 PC 上的下一步操作清单

1. **在真实 Mac (macOS 27) 上克隆仓库并运行 M6 原生验证与 EFI 一键组装**：
   - 详见 `docs/tahoe26/07-native-build.md` 与 `docs/tahoe26/10-install-guide.md`。
2. **在真实 Mac (macOS 27) 上下载 macOS 26 Tahoe 并制作离线安装 U 盘 (Gate B)**：
   - 使用 `softwareupdate --list-full-installers | grep "26\."` 与 `softwareupdate --fetch-full-installer --full-installer-version <26.x>` 获取 `Install macOS Tahoe.app`，写入 U 盘并拷入组装好的 `EFI_READY/EFI`。
3. **在目标 PC 上执行免拆机隔离核验与清空 256GB Ubuntu 盘安装 macOS 26 (Gate C)**：
   - 进入 macOS Recovery 终端，先执行 `diskutil list` 确认 **只有 256GB `INTEL SSDPEKKF256G8L Media` 可见，2TB `WD_BLACK SN850X` 完全不可见**，然后执行清空与安装。
