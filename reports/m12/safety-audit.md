# M12 安全审查

真实Git根为授权Lab子目录，父级独立Git未作为工作仓库。开发前及交付检查核对父Git
24个文件哈希、历史M9–M11/许可证/补丁1105项、所有受保护硬件代码、实际源码哈希。
机器可读最终核验见integrity-review.json。

全部主动源码、输出、TMP、缓存、数据、报告、辅助Git/发布准备写入留在Lab。
检查真实路径、父链symlink/reparse、普通文件hardlink、拥有者；实际Codex沙箱为
workspace-write，但其可写根比Lab更广，因此**不声称操作系统实现绝对Lab隔离**。
路径检查是额外防护，不能消除所有TOCTOU或审计不可见的系统内部行为。
Apple工具只读当前安装；编译/子进程显式使用Lab内TMP/cache，并禁用Core Dump。
未主动写入系统或工作区外文件；这不是对所有系统服务内部写入的全机审计承诺。

| 操作 | 本轮记录 |
|---|---|
| sudo/管理员权限/全局Git配置 | 未使用/未修改 |
| 系统设置/SIP/启动安全/EFI/NVRAM/APFS/Kernel Collection | 未修改 |
| Kext Bundle/签名/安装/注册/加载/内核运行 | NOT RUN |
| 原设备绑定/初始化门禁 | 保留，Navi44绑定拒绝；hardwareInitializationAllowed及Core hardwareAllowed为false |
| GPU/PCI/MMIO/DMA/ROM/Firmware/显示状态/Metal/Vulkan/OpenCL | NOT RUN |
| Windows连接/修改 | NOT RUN |
| SDK/KDK/Lilu/MacKernelSDK/全局工具下载或安装 | NOT RUN |
| 上游Makefile/安装器/旧finalizer/未审查第三方脚本 | 未执行 |
| GitHub main/force/tags/all/mirror/Actions | 未修改/未执行 |
| 网络参考 | 经任务授权只读Apple公开资料、固定XNU/Cobalt小量文本和GitHub元数据 |
| GitHub写入 | 用户独立批准fd9b9032后，仅精确推送sync/m9-m11-sanitized；远程SHA核验一致 |

推送默认网络沙箱失败，随后针对该已授权Git命令扩大网络访问；没有sudo或管理员
提权，也没有把后续编译切到扩大权限。现有凭据仅通过get读取，helper忽略store/erase，
凭据不打印或保存。自动审批没有拒绝该授权动作。两次网络/凭据失败退出128及最终
成功退出0均保留，main仍6b088ba。没有通过GitHub建议链接自动创建PR。

原M9/M10/M11历史及原始本地报告保持不变。干净发布历史不含三者原提交，新增
130个可达对象逐一审查；不含SDK、二进制、原始日志、私人路径或Token。
M12代码和当前实验产物没有推送。本地提交允许，但其私人原祖先不能直接发布。

CPU-only测试仅运行受审查源码生成的用户态程序，Kernel对象/布局探针/正负Kext类型
文件从未执行。ASan/UBSan/TSan和静态分析覆盖范围、未验证项在test-results.json。
解析输入有界，使用既有固定种子；编译串行/线程有限，全部子进程有超时。
