# 07 — Apple Mac（macOS 27）原生构建与 EFI 组装指南 (macOS Native Build Workflow — M6)

您的真实 Apple Mac 运行的是 **macOS 27**。我们专门为您准备了两个一键式 Python 脚本（已推送至 GitHub `tahoe26-dev` 分支）：

1. [`tahoe26/scripts/run_mac_native_verification.py`](../../tahoe26/scripts/run_mac_native_verification.py)：
   - 在 macOS 27 上自动检测 Xcode / Apple Clang 与 SDK；
   - 运行本项目的便携式 CPU-only 测试套件（4 套 Python + 171 项 C++ 断言 + 4000 组变异测试）；
   - 将全部 9 个 Navi44 Core 翻译单元交叉编译为 `-target x86_64-apple-macos11.0` Mach-O `.o` 文件并执行 `nm -u` 符号审查；
   - 若安装了 `iasl` (`brew install acpica`)，自动将 `tahoe26/opencore/acpi/*.dsl` 编译为 `.aml`。
2. [`tahoe26/scripts/assemble_efi_on_mac.py`](../../tahoe26/scripts/assemble_efi_on_mac.py)：
   - 自动将下载的官方 `OpenCore-1.0.8-RELEASE` 与官方 Kext 组装到 `build/efi-staging/EFI`；
   - 自动编译 4 个 `.aml`（包含强制开启的 `SSDT-NVME-PROTECT.aml` 免拆机屏蔽 Windows 盘保护表）；
   - 自动调用 `macserial` 生成本地唯一的 `MacPro7,1` 序列号（不污染 Git 仓库）；
   - 自动调用官方 `ocvalidate` 验证生成的 `config.plist` 零错误。

完整终端命令请直接参阅 [`docs/tahoe26/10-install-guide.md`](10-install-guide.md) 第二部分。
