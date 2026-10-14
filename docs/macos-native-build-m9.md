# M9 真实 macOS 编译与复现

本阶段只编译/运行 CPU Host，Native 仅生成 Object。测试必须在授权的项目
工作区和真实文件沙箱中运行；脚本路径检查不能替代系统沙箱。
不运行衍生 Makefile，不下载/安装依赖，不签名/加载驱动，不访问 GPU。

## 已验证环境

- macOS 27.0.1 / 26A434，arm64；Xcode 27.0 / 27A266a。
- Apple Clang 21.0.0 / clang-2100.3.34.2，macOS27.0 SDK。
- Python 3.14.5 已存在；本次未安装。Xcode 自带 Python 3.9.6 不满足 3.11+。
- CMake 入口已静态审查，本机 PATH 中没有 CMake，本轮未运行或安装它。
- x86_64 运行未尝试；没有确认现有 macOS Rosetta，不触发其安装。

## 本机完整复现命令

先读根 AGENTS.md、安全文档与两个入口。只在本轮授权的目录内运行：

```sh
cd PROJECT_ROOT
PYTHON_EXECUTABLE \
  -I -B -X utf8 run_m9_macos_checks.py \
  --compiler /Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++ \
  --sdk SDK_ROOT
```

其他机器必须先核查其已有 Python、`xcrun --find clang++` 和
`xcrun --sdk macosx --show-sdk-path`，替换为实际绝对路径。
此矩阵专用于本轮 arm64 Mac，x86_64 程序始终只编译/链接。

入口依次执行 arm64 Host、x86_64 编译/链接、arm64 ASan/UBSan、744 组差分、
2400 组固定种子解析变异、实际故障 canary、Native Object 和静态分析。
每个编译/测试子进程最多 60 秒；差分最多 30 秒；Host 外层预算 600 秒。
串行且输入规模有限。重复验证不累计为新增测试。

独立 Host 可以使用 `run_host_tests.py` 的 `--arch arm64` 或
`--arch x86_64 --compile-only --skip-python`；未提供 `--sdk` 时只取
xcrun 的 stdout 路径，stderr 诊断保存在日志中。

## flags 与输出

Host Core：C++17、`-fno-exceptions -fno-rtti -ffreestanding`、严格警告、
`-Wframe-larger-than=4096 -O1 -g`、显式 `-arch/-isysroot`、macOS 部署标记 13.0。
部署标记只用于编译/链接，不是 macOS 13 的运行兼容性证明。

Native 额外使用 `-DKERNEL -DKERNEL_EXTENSION -mkernel -fapple-kext -nostdinc++`
及 `-fno-stack-protector -mno-red-zone`，真实 Kernel.framework 作为系统头文件路径。
没有伪造 Apple 类型，也没有将 Native 源码加入 Host 链接。

产物位于 `build/m9-arm64`、`build/m9-x86_64`、`build/m9-sanitized` 和
`build/m9/native-x86_64`，全部排除于 Git。用户态四个 x86_64 程序已链接，未执行。
SDK 本体未复制/重分发；头文件依赖及 SHA256 见报告 JSON。

## Native 验收范围

`darwin_native.cpp` 验证真实 IOReturn、IOMallocAligned/IOFreeAligned 和 IOLog。
`m9_native_compile.cpp` 只检查真实 OSObject、OSData、IOBufferMemoryDescriptor
引用计数 API 可编译；retain/release 没有在内核运行。另编译九个 Core 和契约，
合计 12 个 x86_64 内核选项 Object。

原始 Adapter 仍只有内存/日志/NodePool callbacks，没有实现真实 Snapshot owner
或 ExecutionOps 线程串行化。Buffer prepare/complete、长期输入存活、关闭时借用撤销、
锁和 stop/free 路径均未验证，不能从编译探针推断这些已完成。

Native 外部引用包含 `_IOMallocAligned`、`_IOFreeAligned`、`_IOLog`，Core 还有
`_memcpy`、`___bzero` 和跨模块 C++ 符号。未验证目标 Intel 内核导出或最终链接闭合。
无异常/RTTI 对象检查不等于生产内核 ABI 认证。

证据见 `reports/m9/test-results.json`、`macho-audit.json`、`native-audit.json`、
`header-dependencies.json` 和 `commands.json`。完整本地原始日志见
`reports/m9/test-logs.zip` / `log-index.json`，不自动上传。
