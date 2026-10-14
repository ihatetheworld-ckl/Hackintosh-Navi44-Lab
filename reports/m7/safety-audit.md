# M7 安全审查与边界

## 授权及执行

唯一主动写入目录：D:/CodexWorkSpace/黑苹果研究/Hackintosh-Navi44-Lab。
使用现有 workspace-write 沙箱；沙箱允许范围比 Lab 更广，Lab 约束另由路径检查和固定 allowlist 执行。
没有请求 Full Access / 管理员 / require_escalated 或扩大权限。
路径检查拒绝 ..、越界 resolve、符号链接、NTFS reparse 与多硬链接；写入前核对现有父路径。
这不是独立 OS 审计，也不能证明竞态环境下绝对防逃逸。

本轮执行的进程：既有 Python、项目内已核对归档的 portable Clang / llvm-nm / symbolizer、
本项目 CPU-only exe、只读 Git status、工作区副本 Git apply 检查/重放。
网络仅使用网页阅读，不执行或克隆远程代码；上游脚本只读。
TMP/TEMP/CLANG_MODULE_CACHE_PATH 和 sanitizer log_path 指向 Lab；-B 禁止 Python pycache。
编译串行，测试进程有超时，固定 2400 次输入变异，不使用无限 fuzz 或 GPU benchmark。
运行前审查 source allowlist；Core/Host 不链接 device.cpp/plugin.cpp/IOKit。
宿主模型没有 PCI/BAR/MMIO/ROM/DMA/GPU Queue 方法。
Darwin native 文件从所有 Windows 编译入口排除，没有下载 Apple SDK 或构造替代头文件。

## 构建入口审查

CMake 只有显式 CPU source targets，未新增 install/FetchContent/ExternalProject/custom/pre/post build。
实际 runner 使用 subprocess argv，shell=False；没有远程脚本、包管理器、服务、驱动加载。
M7 重用本项目旧测试 helper，校验明确截断边界，不执行旧 main，不运行 git hook。
历史 fixture 必须存在，避免隐式重新生成。所有 M7 输出独立保存，重跑日志/失败 JSON 有 attempts 副本。
一次性源码转换脚本保留用于追溯，并在已转换/结构不符时拒绝再次应用。

## 执行记录声明

| 类别 | 本代理本轮执行记录 |
|---|---|
| 主动工作区外写入 | 未执行；没有独立系统级审计 |
| Windows 文件/注册表/服务/驱动/全局 PATH 修改 | 未执行 |
| EFI/BCD/BIOS/UEFI/Secure Boot/TPM/BitLocker 修改 | 未执行 |
| 磁盘分区或 Intel 256GB SSD 内容访问 | 未执行 |
| 真 GPU 访问、硬件 API、ROM/MMIO/BAR/固件/提交 | 未执行 |
| kext/SYS 加载与部署 | 未执行 |
| 管理员权限提升或未授权外部代码执行 | 未执行 |
| Git push / remote branch / PR / Release | 未执行 |
| CPU-only sanitizer canary | 已执行，仅故意使本项目子进程报告内存/整数错误 |

操作系统、运行库和 Codex 工具可能生成缓存、错误报告或日志，未做独立系统级观测，
因此不声称物理零写入或绝对零副作用。没有主动结束其他用户进程、重启或改变显示配置。
