# M9 完整开发报告：真实 Apple 工具链验证

日期：2026-10-14，Asia/Shanghai。本机为研发编译平台，未连接 RX 9060 XT 实验。
本报告仅陈述本轮真实执行结果，不累计 M6–M8.5 的历史测试数量。

## 核心验收结论

| 验收项 | 本轮结果 | 证据与边界 |
|---|---|---|
| A macOS 用户态 Core | PASS | 九个 Core/纯解析单元，arm64 编译、链接和 CPU 测试实际完成 |
| B x86_64 Mach-O | PASS | 九个 Core、Host Adapter、契约对象及四个用户态程序已编译/链接；程序运行 NOT RUN |
| C Darwin Native 合法头文件编译 | PASS | 本机 Apple Xcode SDK Kernel.framework；Native、API 探针、九个 Core、契约共 12 Object |
| D 完整 Kext 构建 | NOT RUN | 没有 Kext 链接、Bundle、签名、安装、加载 |
| E 真实 RX 9060 XT / GPU / Metal | NOT RUN | 没有设备绑定、PCI BAR/MMIO、固件上传、图形/计算/显示测试 |

Native 链接和运行均 NOT RUN。x86_64 运行及其 Sanitizer 运行 NOT RUN。
arm64 成功不能代表 i5-12600KF 硬件或 Intel 内核运行成功。

## 接管与完整性

来源：`https://github.com/ihatetheworld-ckl/Hackintosh-Navi44-Lab.git`。
真实 git clone 已执行，未递归子模块，禁用克隆命令的 credential helper/hooks/template。
用户明确批准了仅用于这次克隆的网络权限扩大；编译测试恢复默认 workspace-write 沙箱。

远程 main HEAD 与指定基线相同：
`6b088ba47a1b9f1bc2493cc03e12e2dae94d1d18`，不存在需审查的新增提交或回退。
已创建独立分支 `m9/macos-native-build`，未在 main 开展修改。
origin 唯一且与指定 URL 相同；`git fsck --full` 实际 exit=0。
Git 对象完整性不等于提交签名或上游作者身份认证。

建议的 ~/Developer 路径不在当前可写沙箱内，未创建/覆盖它。
实际项目根为 `PROJECT_ROOT`。
它是新克隆子目录；父目录原有空 Git 工作树保留，不修改其配置/index/history。
核查了真实父路径、所有权、符号链接和普通文件硬链接；没有覆盖既有项目。

已阅读 AGENTS、README、UPSTREAM_SOURCES、Mac handoff/preparation、M8/M8.5 报告
及 M8 安全审查，保留许可与冻结上游来源。背景文档没有被当作扩大授权的依据。

## 本机环境

| 项目 | 实测值 |
|---|---|
| CPU | arm64 |
| macOS | 27.0.1，26A434 |
| Git | 2.54.0，Apple Git-157 |
| 开发目录 | /Applications/Xcode.app/Contents/Developer |
| Xcode | 27.0，27A266a，完整 Xcode |
| 编译器 | Apple Clang 21.0.0，clang-2100.3.34.2 |
| 原生 compiler target | arm64-apple-darwin27.0.0 |
| SDK | MacOSX27.0.sdk，真实本机 Apple SDK |
| 执行 Python | 既有 3.14.5，mise 安装路径；本轮没有安装 |
| 系统/Xcode Python | 3.9.6，低于项目要求；不用于正式矩阵 |
| CMake | PATH 未发现；configure/build/ctest NOT RUN，未安装 |
| Rosetta | 未找到所查安装 receipt；不能仅据此证明绝对不存在。未确认可用，未运行 x86 程序或触发安装 |

真实命令、stdout/stderr、exit 见 `environment.json`。
编译器由 Apple 工具链提供；Python 自身的编译器版本不替代 C++ 编译器证据。

## 实际源码改动

1. `run_host_tests.py`：提前拒绝 Python <3.11，避免旧解释器运行到写日志时才失败；
   macOS 显式选择 SDK/架构；增加 compile-only、ASan/UBSan 和跳过重复 Python 的选项。
   SDK 路径只读 stdout，stderr 原样记日志。生成真实头依赖；分开报告编译、链接和运行。
   原 Windows 默认链接策略保留，不禁用硬件门禁。
2. `core/display.cpp`：Apple 分析器报告 gcd 约分潜在零除数；增加显式 `common==0`
   拒绝保护。既有几何/时钟限制应使正常输入的 gcd 非零，未声称在运行中复现了除零。
   没有屏蔽分析器或放松合法输入约束；原单位/变异和 Sanitizer 重新通过。
3. `run_m9_macos_checks.py`：新建串行、有超时的 Apple 验证矩阵，明确源码 allowlist；
   Mach-O/符号/头文件审查、差分、实际 canary、真实 Native Object 和静态分析。
4. `tests/fixtures/m9_differential.py`：迁移已审查的纯 Fixture 函数，避免导入历史
   runner 执行顶层 writer；已有损坏合成 ELF 改为只读验证，绝不隐式再生成。
5. `tests/unit/m9_native_compile.cpp`：真实 OSObject、OSData、Buffer 引用 API 的独立
   编译探针；不链接或执行，不伪造 Apple SDK。Native 源码注释更新为实际对象编译状态。
6. README、Mac 说明、忽略规则和本阶段报告；精确变更清单见 `changed-files.json`。

未修改 CMake 源码 allowlist、device/plugin/profile/Makefile 硬件门禁、历史 runner、
许可证、上游 pin、历史报告和补丁。Windows 本轮执行 NOT RUN，不能宣称已重跑 Windows。

## 真实测试结果

| 类别 | 最终一次矩阵的实际结果 |
|---|---|
| Python 四套 | 56+11+22+2=91 PASS，2 SKIP，0 FAIL；91 中包含 4 个静态安全断言 |
| arm64 C++ | m65 34、m7 31、m8 96，共 161 PASS、0 FAIL |
| EDID/AtomBIOS 有界变异 | 2400 输入，479 accepted、1921 rejected，invariants PASS |
| N44Q 有界变异 | 800 输入，10 accepted、790 rejected，invariants PASS |
| C++/Python 共享差分 | 744 合成输入，0 差异 |
| 原解析器变异差分 | 2400 输入，seed=759070，0 差异 |
| arm64 ASan+UBSan | 161 C++ 断言、744+2400 解析输入、2400 显示及800 Query 变异通过 |
| ASan canary | 真实 heap-buffer-overflow 被检测，子进程预期 exit=1 |
| UBSan canary | 真实 signed integer overflow 被检测，子进程预期 SIGABRT（exit=-6） |
| Apple 静态分析 | 九个 CPU 源文件加契约，十个编译单元，最终零 warning |
| x86_64 Host | 编译/链接 PASS；测试程序实际运行 NOT RUN |
| Native/Kernel Object | x86_64 共12个对象编译 PASS；链接/执行 NOT RUN |
| 真实 Navi44 Discovery | SKIP：仍无已验证的本卡 capture |
| 真实 gfx1200 ELF/shader | SKIP：仍无真实 gfx1200 编译产物；已有 macOS SDK 不解除该限制 |

这些是已有逻辑在真实 Mac 的复现，不是新增 161/91 个设计测试。重复、Sanitizer、
首次失败后的重跑均不额外累加。截断循环和静态断言也没有累计成“GPU 支持总数”。
差分与显示/Query invariants 是不同验证维度，没有虚构对应 Python EDID 解析器。

最终矩阵记录75个外层命令，Host 三个子矩阵分别24/16/20个命令，共135条真实命令记录。
普通编译/链接/测试均 exit=0；仅两个受控 canary 预期非零。历史和失败尝试不计入该数。
完整 argv/exit/time 见 `commands.json` 及各 `reports/m9-*/commands.json`。

Sanitizer leak detection 显式关闭，leak NOT VERIFIED。本机 canary 的 atos 外部符号化
出现启动警告，检测器本身捕获了正确错误；不声称完整符号化或内核内存测试通过。
输入和子进程都有边界；不是无限 fuzz、coverage-guided fuzz 或 GPU 压力测试。

## arm64 / x86_64 Mach-O 验证

使用显式真实 SDK 与 `-arch arm64` / `-arch x86_64`，所有 Core 保留
`-std=c++17 -fno-exceptions -fno-rtti -ffreestanding -Wall -Wextra -Werror`
和4096字节栈帧警告、O1/debug选项。源码/完整命令/对象 SHA 均有记录。

file、Apple nm/otool/lipo 和 Mach-O 头/load-command 实际检查确认：
arm64 CPU=16777228；x86_64 CPU=16777223、subtype=3；对象 MH_OBJECT=1，程序 MH_EXECUTE=2。
LC_BUILD_VERSION platform=1（macOS），minos=13.0、sdk=27.0。
minos 编译标记不能代替 macOS 13 或目标 Intel 机器的运行验证。

`macho-audit.json` 记录两架构的九个 Core、契约和四个程序共28个对象/程序条目。
Host Adapter 另有真实编译产物。Core 未见 throw/personality/unwind、dynamic_cast、
RTTI、STL/常见 C++ new 的未解析依赖；编译命令确实关闭异常/RTTI。

跨模块 C++ 引用和 `_memcpy` / `___bzero` 仍存在。用户态 Core 还会引用 stack-check
符号；内核选项对象显式关闭 stack protector。对象检查不宣称整个 Core 无任何运行时依赖。
没有把 Darwin 符号名称、无 RTTI 或 freestanding 标记等同最终内核 ABI/导出链接成功。

## Darwin Native：真实头文件与生命周期边界

使用现有 macOS SDK 的 `System/Library/Frameworks/Kernel.framework/Headers`，
合法本机 Apple IOKit/IOLib、IOReturn、OSObject、OSData、IOBufferMemoryDescriptor。
头文件依赖来自实际 `-MD`，本轮记录269个 SDK 文件的 SHA256；见
`header-dependencies.json`。未复制 Apple 头文件内容或 SDK 进入项目/Git。
没有下载 MacKernelSDK、Lilu、私有 SDK、ROM 或固件。

独立内核编译选项为 KERNEL/KERNEL_EXTENSION、mkernel、fapple-kext、nostdinc++、
无异常/RTTI、freestanding、no-stack-protector、no-red-zone 和严格警告。
Kernel.framework 作为真实系统 include 路径，不屏蔽本项目警告。

Native 未解析外部 API：`_IOMallocAligned`、`_IOFreeAligned`、`_IOLog`。
这些是对象依赖，不是已在内核分配/释放/日志的执行证据。
原 allocator 保持1..65536字节、对齐<=4096、2次幂及配对释放；vm_size_t宽度断言真实通过。
IOReturn 使用真实 SDK 类型。未加入 IOService、PCI/MMIO、DMA 或设备绑定方法。

NodePool 仍由长期 owner 构造，内部 bool 不是并发锁；必须放在内核栈外并提供
ExecutionOps 的正确线程上下文及串行化。View/Input lease 仍是借用模型。
Host Mock 验证了失败/重入/解析/资源不足情况下的配对归还；这些是 CPU 行为。

Buffer retain/release 和 OSData getLength/getBytesNoCopy 用真实类编译，但探针没有执行。
生产 SnapshotOps 的长期 OSObject 所有权、Buffer prepare/complete、stop/free、
borrow 撤销和真实并发仍未实现/验证。不能用编译探针替代生命周期运行测试。
内核目标符号导出、`___bzero`/memcpy 依赖、OSObject ABI 和完整链接闭合仍需独立阶段。

## 失败保留与修复

- 沙箱 Git 网络失败：本地代理不可达、直接 DNS 失败。获用户网络确认后只执行指定 clone。
- Python 3.9：原入口在写日志时 TypeError；使用既有3.14，入口增加明确版本拒绝。
- 原 Clang Host：九个 Core 编译成功；编译第一个测试时 `iostream file not found`，
  因此当时链接/运行尚未成功。修复显式 SDK 后真实链接和运行成功。
- 初次 SDK 自动查询：xcrun stderr 的 Xcode 沙箱诊断被拼入路径。
  修复为 stdout 路径，stderr 原样保留，没有扩大 Xcode 权限。
- 初次完整矩阵：Apple analyzer 的 display 零除数警告令流程失败。
  加入显式拒绝后重跑矩阵，最后十单元零 warning，没有隐藏首次警告。

本地证据分别位于 `baseline/`、`sdk-query-failure/`、`attempts/analyzer-first/`
和相关 `.log`。失败文件不覆盖 M6–M8.5 历史结果；见日志索引。

## 安全、交付与停止

详见 `safety-audit.md`。测试始终在实际 workspace-write 沙箱中执行，未扩大编译权限。
所有显式文件写入都留在授权项目；TMP/cache/build/log亦在项目。
唯一权限扩大是用户确认的一次 Git clone 网络访问，无 sudo/管理员。

未安装任何组件，未改系统设置、EFI/NVRAM/SIP、驱动或启动策略；未操作 Windows；
没有运行上游 Makefile、安装脚本、GPU API、Kext/SYS 或硬件程序。
历史报告、补丁、许可和门禁字节核对见 `integrity-audit.json`。

交付：本报告、环境、test-results/commands、Mach-O/Native/头依赖、源码 SHA、
安全审查、变更清单、`patches/m9-from-m85.patch`、本地完整原始测试日志包和日志索引。
日志包与编译产物只保留本机，不进入 Git；审核后的文本证据可进入本地提交。
本地提交 SHA 见 ignored 的 `reports/m9/local-commit.json`，避免报告自引用 SHA。

下一阶段建议：首先审查并确认 M9 GitHub 同步内容；其次在单独授权的 CPU/内核工程阶段
解决目标 macOS/XNU版本、导出符号与链接、真实 owner/线程/撤销契约及失败注入。
若需 Rosetta或第三方固定依赖，先核实来源/版本/许可证并征求确认。
完整 Kext、签名、加载、GPU 实验须另行独立授权，本阶段没有启动它们。

M9 完成本地交付后停止，等待用户确认 GitHub 同步及后续研发。未 Push/Force Push/PR/Actions。
