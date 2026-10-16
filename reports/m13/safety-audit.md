# M13 安全记录

实际仓库根为用户授权Lab，父目录独立Git只读hash核对。所有操作目标文件经过
真实路径/父链/所有者/软硬链接检查；拒绝路径穿越。项目TMP/cache显式设置，
Python -I/-B、串行编译、超时、固定种子及有界线程，禁止Core Dump。
实际Codex sandbox可写范围仍宽于Lab，因此不宣称绝对Lab隔离或全机零副作用证明。

主动源码、构建、记录、独立发布Repo写入留在Lab。Apple SDK/工具仅只读使用。
SDK26.5来自既有CLT，默认SDK27只用于明确legacy或负样本，未安装、替换SDK或
更改xcode-select。原始参考文本只在ignored local，不作为include，不重分发SDK。

| 边界 | 记录 |
|---|---|
| sudo/管理员/沙箱扩大 | 未使用 |
| 系统/SIP/Secure Boot/EFI/NVRAM/APFS/KC/启动/显示设置 | 未修改 |
| Kext Bundle/签名/注册/安装/加载/内核执行 | NOT RUN |
| 真实PCI/GPU/BAR/MMIO/DMA/ROM/firmware/queue/shader/Metal/Vulkan/OpenCL | NOT RUN |
| Windows、第二SSD、远程连接 | NOT RUN |
| 新SDK/KDK/工具/第三方组件下载或安装 | NOT RUN |
| 上游Makefile/安装脚本/旧finalizer/第三方脚本 | 未执行 |
| 父Git/全局Git/远程main/force/Actions | 未修改/未执行 |
| GitHub Push | NOT PUSHED；只读查询和项目内发布准备 |
| 网络 | Apple官方资料、GitHub元数据及固定公开源码只读研究 |

hardwareInitializationAllowed/Core hardwareAllowed恒false，Navi44实际绑定门禁保留。
不执行生成的内核对象、布局探针或正负Kext类型文件。新地址/Fence代码只推进CPU
元数据；停止/超时不代表GPU quiescence。没有真实GPU Backend。
父Git与历史字节核验、执行源码hash、编译依赖及发布扫描另有JSON证据。
没有主动指向Lab外写入；没有独立全系统内部cache/log行为审计。
