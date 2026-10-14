# Mac 编译准备与 M9 边界

M9 更新：真实 Apple Clang Host 和 x86_64 Mach-O 已验证；现有 Xcode SDK
包含 Kernel.framework 公开头文件，独立 Native Object 无需获取 MacKernelSDK/Lilu。
实际结果与复现见 [M9 报告](../reports/m9/development-report.md) 和
[Mac 原生编译说明](macos-native-build-m9.md)。下文保留 M8.5 的准备时状态；
未来完整 Kext 的依赖、链接与硬件边界仍未解除。

## 当前已经完成的工作

M8 在 Windows 上使用 LLVM-MinGW 20261006 / Clang 23.1.3 完成纯 CPU 构建。
M8.5 在独立输出目录重跑原回归：Python 91 PASS/2 SKIP，C++ 161 PASS，
744 差分输入无差异；有界变异、ASan/UBSan、Core 无异常/无 RTTI 与静态检查通过。
这些不是 Mac、Kext 或 GPU 结果。Native Darwin、真实 gfx1200 Code Object、
真实 Navi44 ROM/显示器 EDID、显示与 Metal 仍按历史限制标记。

## 克隆后已有与缺失的依赖

纯 Host 所需 Core/Host/Contract、C++ 测试、Python 实现、合成 Fixture、
LLVM 常量参考均包含，不需要 Lilu、MacKernelSDK、Cobalt64、固件或 ROM。
已有 Python 3.11+ 和 C++17 编译器即可开始；不自动安装依赖。

Windows 历史入口依赖固定 lab-relative LLVM-MinGW 的 `.exe`、Windows
Sanitizer DLL、`-static` 和 ZIP 完整性验证，不能直接作为 Mac 命令。
历史报告中的 Windows 绝对路径是当时 argv 记录，不是新构建配置。
源码/CMake 使用相对项目路径；GPU 程序属于未编译的静态参考。

Mac 必须使用合法的 Apple Clang 与真实 macOS SDK。
若 Xcode/Command Line Tools 不存在，应记录环境阻碍，安装须另行授权。
使用现有工具的只读核验例子：

~~~sh
xcrun --find clang++
xcrun clang++ --version
xcrun --sdk macosx --show-sdk-path
~~~

## M9 纯 Host 构建候选

先审查 `run_host_tests.py` 与 `CMakeLists.txt`，在已经授权的 Mac 项目目录执行。
这些命令在本轮 Windows 环境没有证明 Mac 可编译：

~~~sh
python3 -I -B -X utf8 run_host_tests.py --compiler "$(xcrun --find clang++)"
~~~

入口只编译纯 CPU sources，串行运行 C++/Python/固定种子有限变异，产物与 TMP 留在项目。
它不包含旧 Windows 差分/Sanitizer 管线；M9 应再移植这两项并单独报告。
可选 CMake（仅当已安装）：

~~~sh
cmake -S . -B build/m9-host -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_COMPILER="$(xcrun --find clang++)"
cmake --build build/m9-host --parallel 1
ctest --test-dir build/m9-host --output-on-failure --parallel 1
~~~

Apple Silicon 上首先验证 arm64 Host；其次独立研究 x86_64 Host 目标：
使用 `-DCMAKE_OSX_ARCHITECTURES=x86_64` 输出到另一个项目内目录。
运行 x86_64 Host 可能需要已安装的 Rosetta；本项目不自动安装它。
不能运行时只报告编译，不将 runtime 记 PASS。
arm64 用户态通过不能代表 x86_64 Kext ABI 或 12600KF/Navi44 支持。

## Darwin/Kext 构建状态

`platform/darwin_native.cpp` 仍是静态草案，根 Host 构建不包含它。
未来真实 Native object 需要合法 SDK、固定 MacKernelSDK/Lilu 头、
对应 XNU 版本、Darwin 类型/符号/布局和生命周期审核。
首先做独立 Native object 编译/undefined symbol 审查；不能套用 Windows COFF 结果。
原衍生 Makefile 仍禁用，不解除 `hardwareInitializationAllowed=false`。

本次 `Kext Build = NOT RUN`。M9 推荐顺序：

1. 校验克隆分支、提交、许可证、内容清单及门禁。
2. Apple Clang arm64 Host 构建与功能回归。
3. x86_64 Host 编译/运行分开记录，移植差分与 Sanitizer。
4. 真实 SDK Native object 编译、ABI/符号与资源生命周期分析。
5. 依据结果决定是否值得申请下一独立 Kext 工程验证阶段。

本交接不授权驱动签名、安装、加载、硬件绑定、GPU、EFI/分区、macOS 部署
或远程操作。工具缺失时报告 NOT RUN；不得下载非官方 Apple SDK。
