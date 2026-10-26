# 07 — Apple Mac 原生构建与验证流程 (macOS Native Build Workflow — M6)

由于 Windows 主机并非真实的 Darwin 内核构建环境（不能将 Windows PE/COFF `.exe`/`.o` 当作 Mach-O Kext），我们为用户的真实 **Apple Mac** 编写了全自动、只读安全的原生构建与 Mach-O 校验脚本：[`tahoe26/scripts/run_mac_native_verification.py`](../../tahoe26/scripts/run_mac_native_verification.py)。

## 在 Apple Mac 上执行的精确步骤

1. 在您的 Apple Mac 上打开终端，进入您授权的工作目录并克隆/拉取本仓库：
   ```sh
   git clone https://github.com/ihatetheworld-ckl/Hackintosh-Navi44-Lab.git
   cd Hackintosh-Navi44-Lab
   git fetch origin
   git checkout tahoe26-dev
   ```
   *(注：若 `tahoe26-dev` 尚未经 Gate E 推送到 GitHub，也可直接将本目录同步到 Mac，或批准 Gate E 推送 `tahoe26-dev` 分支)*
2. 运行 Mac 原生验证脚本（无需 `sudo`，不加载任何 Kext，不修改 Mac 系统设置）：
   ```sh
   python3 -I -B -X utf8 tahoe26/scripts/run_mac_native_verification.py
   ```
3. 脚本将自动完成：
   - 核实 `xcrun clang++ --version` 与 macOS SDK 路径；
   - 在 Mac 本机运行完整 Python + C++17 `171 PASS` 单元测试与 `4000` 组有界变异测试；
   - 使用 `-target x86_64-apple-macos11.0 -fno-exceptions -fno-rtti -ffreestanding -Wframe-larger-than=4096 -Wall -Wextra -Werror` 编译全部 9 个 Core 翻译单元为真实 Mach-O `x86_64` `.o` 对象；
   - 使用 `xcrun nm -u` 审计所有 Mach-O 对象的未定义符号，并将结果写入 `tahoe26/tests/native/mac-native-report.json`。
4. 将生成的 `tahoe26/tests/native/mac-native-report.json` 回传至本 Windows 工作区，即可将 Core 模块状态升级为 `VERIFIED_NATIVE_BUILD`。
