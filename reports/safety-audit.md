# 实际安全与获取记录

日期：2026-10-13。

- 独立新目录创建前检查不存在；未覆盖先前研究报告。
- Git clone 仅公开仓库，使用 `--no-checkout`，固定提交后检出；不递归初始化 submodule，不运行 hooks/脚本。
- Git 命令使用进程级 `core.hooksPath=NUL`、`maintenance.auto=false`、`gc.auto=0`；不修改 global Git。
- sandbox 网络最初因 TLS credential 不可用失败，已对具体源码获取请求网络授权；没有请求管理员权限。
- `safe.directory` 仅用于已知克隆目录的单条命令参数，解决不同 sandbox 用户所有权检查，不写全局配置。
- 仅下载 Linux/LLVM 文本头文件；没有安装 compiler/SDK、下载驱动二进制或固件。
- 执行的是本项目已审查的 Python 源码转换、CPU-only 测试及报告脚本；没有执行上游程序。
- Python 使用现有实际 executable，`-I -B`；TMP/TEMP 显式指向 lab/tmp。
- 上游两个 snapshot 的 `git status --porcelain` 为空；patch 检查不应用修改。
- 开发副本 Makefile 拒绝上游构建，Navi44 不绑定，init 恒拒绝，host CMake 不链接硬件代码。
- 真实显卡、EFI、分区、Windows 设置、启动、账户、服务及驱动没有被项目主动访问或修改。

源码门禁与上述操作记录不是操作系统审计证明，也不是绝对零缓存承诺。本会话没有建立单独只允许 lab 写入的新 OS sandbox。
完整参考树包含危险脚本和硬件代码，保留供阅读；不要执行。完整代码安全审计和 C++编译仍未完成。
