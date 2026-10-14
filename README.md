# Hackintosh-Navi44-Lab

RX 9060 XT / Navi44 / gfx1200 的 **CPU-only** 驱动研发项目。
M8 已完成 Windows 离线解析与数据模型验证；M8.5 已完成 GitHub 迁移。
M9 已在真实 macOS / Apple Clang 上完成 arm64 CPU 测试、x86_64 Mach-O
及真实 Kernel.framework 头文件的 Native 独立对象编译。
M10 已加入 Snapshot/Buffer 生命周期、Host mutex Mock 与两架构非部署型部分链接。
具体证据见 [M10 报告](reports/m10/development-report.md)；部分链接仍是 MH_OBJECT，
完整 Kext 链接、内核运行和真实 GPU 功能均 NOT RUN。
目标仓库由用户创建为 Public，首次上传已确认；后续推送仍需用户确认。
EDID、AtomBIOS、Discovery、Firmware、ELF、N44I/N44Q 是静态软件模块。
真实 GPU 显示、Vulkan/Metal、WindowServer、Native 链接/运行及 Kext 构建均未验证。

## 代码与证据

| 路径 | 内容 |
|---|---|
| `development/AMDRadeonRDNA4-Navi44/core` | 无异常/无 RTTI 的纯逻辑、显示能力和 ABI |
| `development/AMDRadeonRDNA4-Navi44/src` | 解析模块及有门禁的上游硬件源码；硬件源码不加入 Host 构建 |
| `development/AMDRadeonRDNA4-Navi44/host` | Python 参考实现、STL Host Adapter、Mock |
| `development/AMDRadeonRDNA4-Navi44/platform` | 平台契约、Darwin 静态草案；Native 不进入 Host |
| `tests` | C++ / Python 测试与合成 Fixture |
| `docs` | 设计、Mac 准备与 M9 交接 |
| `reports` / `patches` | M6/M6.5/M7/M8 关键报告、固定来源和增量补丁 |
| `upstream/references` | 两份有许可证的固定静态头文件；不含完整参考克隆 |

- [M8 完整报告](reports/m8/development-report.md)、[测试](reports/m8/test-results.json)、
  [命令与退出码](reports/m8/commands.json)、[安全审查](reports/m8/safety-audit.md)。
- [M8.5 迁移报告](reports/m85/development-report.md)、[Mac 编译准备](docs/macos-build-preparation.md)、
  [Mac Codex 交接](docs/macos-codex-handoff.md)、[固定上游与许可证](UPSTREAM_SOURCES.md)。
- [EDID](docs/edid-parser-design.md)、[AtomBIOS](docs/atombios-parser-design.md)、
  [显示模型](docs/navi44-display-capability.md)、[Darwin](docs/darwin-adapter-m8.md)、
  [候选 ABI](docs/cobalt-production-abi.md)、[M8 增量补丁](patches/m8-from-m7.patch)。

## 安全的验证入口

从项目根目录运行；需要已有 Python **3.11+**，不自动安装依赖：

~~~text
python -I -B -X utf8 run_m85_offline_tests.py
~~~

以上入口仅适用于已具备固定 LLVM-MinGW 工具链的 Windows 原工作区。
新 Windows 克隆不含工具链；来源、版本和 SHA 见 UPSTREAM_SOURCES.md。
日志位于 `reports/m85/validation`，产物在 `build/m85/validation`，临时文件在 `tmp`。
串行、固定种子、每进程有超时；Sanitizer canary 会让本项目子进程发生预期 CPU 错误。

Mac 的纯 Host 构建可使用现有 Apple Clang / CMake，或新增的便携入口：

~~~text
python3 -I -B -X utf8 run_host_tests.py --compiler /absolute/path/to/clang++
~~~

M9 已实际验证 Mac 入口；必须选择现有 Python 3.11+（Xcode 自带 3.9 不满足）。
入口在 macOS 明确选择真实 SDK，支持 `--arch` 和 `--compile-only`，不自动安装 Rosetta。
完整串行验证与证据见 [M9 报告](reports/m9/development-report.md) 和
[M9 复现说明](docs/macos-native-build-m9.md)。x86_64 程序运行为 NOT RUN。
`CMakeLists.txt` 显式列出 CPU-only 源码，没有 FetchContent/install/GPU/IOKit backend。
原 Makefile 有立即失败门禁。不得运行衍生目录用户态 GPU 程序或上游安装脚本。

## 历史与发布边界

旧 stage runner/finalizer/prepare 脚本保留为研发追溯，不作为 Mac 安装入口；
直接运行它们会重写旧 stage 输出，禁止未经审查调用。
原本地快照、克隆、工具链、ROM 和完整日志不删除，但不进入首次提交。
历史报告引用的一部分大日志/快照仅在 Windows 原工作区存在。
M8 原 README 的迁移前快照保存在本地 `reports/m85/local-history`。

Git 文本使用 LF；历史补丁和合成 bin 字节保留。旧 SHA 是 Windows 原工作区字节证据，
不是新克隆 LF 文件的校验清单；Git blob 对应的迁移清单另行生成。
没有活动 Git Submodule，也没有 GitHub Actions Workflow。
门禁不替代操作系统沙箱：全部主动写入必须留在当前明确授权的项目根目录。

根 LICENSE 为 BSD-3-Clause，局部例外见 NOTICE；上游版权声明保留。
本项目尚不能作为 RX 9060 XT 可部署驱动或可日常使用的 macOS 方案。
