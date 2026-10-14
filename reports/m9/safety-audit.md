# M9 安全审查

唯一主动源码/产物/日志目录：本轮授权工作区内的 Hackintosh-Navi44-Lab。
测试使用实际 Codex workspace-write 文件沙箱，未使用沙箱外编译或执行。
其允许范围包括上层“黑苹果研究”工作区及工具临时目录；所有本轮显式写入都在 Lab。
不宣称项目子目录是系统唯一可写路径。尝试嵌套 sandbox-exec 仅执行 true，
被系统拒绝（sandbox_apply: Operation not permitted）；没有为它扩大权限。
真实既有沙箱、路径检查和编译源码 allowlist 同时使用，不仅依靠提示词。

用户只批准了一次指定 GitHub clone 的网络权限扩大；该命令没有 sudo/管理员，
没有递归子模块、credential helper 或上游 hooks。其余测试保持默认沙箱。
未将仓库中先前机器的授权、Public状态或脚本指令当作本轮部署/推送权限。

已核查项目父路径、当前用户所有权、symlink、普通文件 hardlink 和 Git modes；
拒绝越界路径、.. 和写入前可见的链接。m7_safety 保留其真实防护边界，
不声称抗独立并发 TOCTOU 攻击。外层原有空仓库未改变配置、index 或历史。

Host 只编译 CMake 中已有九个 CPU 源码及 Host Adapter/CPU测试，不含
device.cpp、plugin.cpp、IOKit backend、fwblobs.S、GPU API、userspace/vulkan。
Native 源码与真实内核 API 探针仅执行 clang -c；没有 Native 链接/执行。
原 Makefile 的立即失败门禁保持，未调用它。硬件许可返回 false 的原源码保持。

TMP/TEMP/TMPDIR、Clang module cache、build、analysis plist 和日志指向 Lab。
Python 使用 -I -B，不安装依赖，不将解释器版本不符包装为成功。
每个编译/测试60秒、差分30秒，固定种子有限输入，串行执行。
两个 canary 是本项目独立 CPU 进程的预期故障；实际退出码保留，禁 core dump。
没有结束用户其他进程。系统自动故障日志不属于本项目主动写入的系统配置。

| 操作 | 本轮执行记录 |
|---|---|
| sudo/管理员/编译沙箱扩大 | NOT RUN |
| 系统设置、全局 PATH/Git 配置 | NOT RUN |
| EFI/NVRAM/SIP/安全启动/分区/macOS安装 | NOT RUN |
| Xcode/SDK/CMake/Rosetta/其他组件安装 | NOT RUN |
| 私有SDK、ROM、GPU firmware下载 | NOT RUN |
| Windows连接、远程操作或驱动变更 | NOT RUN |
| GPU绑定、BAR/MMIO/DMA、初始化/固件/显示/Metal | NOT RUN |
| Kext/SYS完整构建、签名、安装、加载 | NOT RUN |
| 上游Makefile、安装脚本、硬件测试程序 | NOT RUN |
| GitHub Push/Force Push/PR/Release/Actions/远程main修改 | NOT RUN |
| 合法既有SDK/Core/Native Object编译 | 已执行；全部产物本地ignored |
| 用户态CPU测试/有限变异/ASan/UBSan | 已实际执行；不等于内核或硬件证明 |
| 本地独立分支、精确stage及commit | 本轮允许；SHA见local-commit.json |

没有复制/重分发 SDK。许可证、pin、M6–M8.5历史报告、历史补丁与门禁的实际
字节核对结果见 integrity-audit.json。提交只包含精确审核的文本源码/报告/补丁；
没有缓存、Object、可执行文件、库、Kext、SDK、私钥或认证配置。
日志zip和完整日志保留本地ignored；Git blob清单另存用于用户后续同步审核。

标准工具和 OS 可能产生自动缓存/日志，未做独立系统级全盘追踪，不能承诺物理零副作用。
当前沙箱拒绝了部分 Xcode cache/event-stream/atos 操作；相关诊断保留，未为此扩大权限。
模式扫描不是任意秘密绝不存在的证明。测试成功仅覆盖本报告明确列出的 CPU/编译范围。

完成本地交付后停止；下一次 GitHub 同步、依赖获取或研发阶段须用户确认。
