# M11 安全记录

cwd/top level/real path为授权Lab；所有权、祖先及受操作文件链接/硬链接检查。
父目录独立.git只读hash，对应字节在交付审计重新比较。原M6–M10报告/补丁/许可不覆盖。
使用现有workspace-write系统沙箱，真实权限还包括父工作区/temp，不能声称Lab是OS
唯一可写目录。m7_safety提供逐路径检查，不能代替沙箱或防御TOCTOU证明。

源码、文档、Git分支/提交、独立发布仓库和所有显式产物路径均在Lab。
runner的TMP/TEMP/TMPDIR及Clang cache均明确指向Lab；Python -I/-B、串行child超时、
固定有限输入与两线程。**一次早期直接Clang探针没有覆盖TMPDIR，不能证明该次工具
自动临时文件全部在Lab**；之后编译/测试均改为明确临时目录。没有独立全盘副作用审计，
不把工具自动cache/log等同物理零写入证明。这个限制公开记录，不篡改原始事实。

所有Kernel输出仅编译/链接/静态读取，包含允许的独立MH_KEXT_BUNDLE文件及隔离的
Host-import链接负样本。没有.kext目录/Info.plist/匹配规则、部署流程、服务注册或执行。
KMOD metadata来自真实Apple宏，项目自身start/stop拒绝运行；没有伪造Apple API定义。
保护系统的前提仍是绝不安装/加载，文件链接不解除任何门禁。

| 项目 | 本轮记录 |
|---|---|
| 管理员/sudo/权限扩大 | NOT RUN |
| 系统设置/安全策略/SIP/EFI/NVRAM/APFS/KC/启动项 | NOT RUN |
| Kext Bundle/签名/注册/安装/加载/内核执行 | NOT RUN |
| PCI设备/BAR/MMIO/DMA/固件/GPU/Metal/Vulkan/显示 | NOT RUN |
| Windows主机连接/修改 | NOT RUN |
| 额外SDK/工具/Lilu/MacKernelSDK/Rosetta安装或获取 | NOT RUN |
| 上游Makefile/安装脚本/第三方脚本/Actions/外部CI | NOT RUN |
| 全局Git配置/远程main/Force Push/远程历史修改 | NOT RUN |
| GitHub推送 | NOT PUSHED；等待独立批准 |
| 网络 | 只读已授权公开GitHub/API与Apple资料；无第三方可执行依赖获取 |
| Lab外显式主动写入/父Git修改 | 未执行；工具自动临时边界限制如上 |

原硬件初始化false及N44I/N44Q未验证能力关闭保持。精确stage，禁止SDK/object/log/token
加入Git。新公开记录使用PROJECT_ROOT/PYTHON_EXECUTABLE/SDK_ROOT标签，原始argv本地
ignored。M11研发branch继承原私人历史，同样不得自动推送。
