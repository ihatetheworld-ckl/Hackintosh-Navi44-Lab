# M6.5 实际构建结果

报告日期：2026-10-14。最终验证时间：2026-10-14T00:37:40.503321+08:00。

| 项目 | 结果 |
|---|---|
| 编译器 | Clang23.1.3 / LLVM-MinGW20261006 UCRT x86_64 |
| 发布来源 | [官方release](https://github.com/mstorsjo/llvm-mingw/releases/tag/20261006) |
| 归档SHA256 | `317492c456aa27ee607a5919f1d2d38dcdc1112516a24d0bf4b00d078f52d17a` |
| 核验 | 官方GitHub asset digest与本地archive一致；非独立签名 |
| 普通C++ unit/probe | 编译、链接、实际执行PASS |
| ASan/UBSan unit/probe | 编译、链接、实际执行PASS |
| canary | 编译PASS；预期非零退出与相应diagnostic已验证 |
| CMake/Ninja | 未运行，不是本次构建依赖 |
| macOS Kext | NOT RUN，不产生安装包 |

实际命令使用显式clang++路径、C++17、警告视为错误、项目include、纯逻辑源文件。
完整可复现argv：[commands.json](m65/commands.json)；工具记录：[toolchain-provenance.json](m65/toolchain-provenance.json)。
Python/Clang启动后会正常读取Windows运行库，未写系统编译器目录或修改PATH。
早期ASan DLL依赖遗漏、盘符log_path和UTF-8问题已修复；历史尝试保留在m65/attempts。
