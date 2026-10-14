# M10 安全审查

所有命令在指定Lab根执行；Git root核查一致。用户与目录owner一致，根/祖先和既有
文件未观察到symlink、多hardlink；写入前使用现有m7_safety路径检查。
Actual workspace-write沙箱仍生效；本轮编译/测试/链接没有申请扩大权限。
允许范围包含上层工作区和工具temp，所有显式写入均限Lab；不能仅靠提示词宣称隔离。

父Git只读哈希；不得由Lab操作覆盖父index/config/refs/history。Lab创建M10独立分支，
M9现有提交保留。所有原报告/日志/补丁保留，禁止历史finalizer执行。
只读公开GitHub连接核对远程，M9人工推送门禁尚未通过，未上传任何blob/commit/ref。
独立脱敏tree只在本地Git对象/独立index生成，正常Lab index未因此重置。

CPU源码allowlist排除device/plugin/硬件/firmware/vulkan。原门禁false和Makefile失败保持。
Native源只clang -c / ld -r，严格MH_OBJECT，无动态加载/入口/初始化，产物不执行。
实际Apple头来自既有SDK；不复制其源码。公开导出数据的pin/hash是参考，不是目标内核链接stub。
没有伪造函数/Apple头/IOKit对象去获得PASS。Host数组/Mutex与真实Kernel类型明确隔离。

TMP/cache/analysis/build/log均在Lab，Python -I/-B。每child有超时、串行编译，
600组失败注入和240次有限并发，无持续占用CPU或无限fuzz。
M9旧行为回归证明使用有界递归callback并仅返回预期exit1，没有内核或硬件故障。
ASan/UBSan/TSan只运行Host；KernelAPI不在用户态调用。物理owner销毁、Kernel同步仍未验证。

| 项目 | 记录 |
|---|---|
| sudo/管理员/权限扩大 | NOT RUN |
| 全局Git/PATH/系统设置 | NOT RUN |
| EFI/NVRAM/SIP/启动安全/APFS/分区/快照 | NOT RUN |
| 新工具/SDK/Xcode/Rosetta/组件安装 | NOT RUN |
| Kext Bundle/完整链接/签名/加载/Kernel Collection | NOT RUN |
| GPU/PCI BAR/MMIO/DMA/固件/显示/Vulkan/Metal | NOT RUN |
| Windows连接/操作 | NOT RUN |
| 上游Makefile/安装脚本/外部CI/Actions | NOT RUN |
| GitHub推送/PR/main修改/Force Push | NOT RUN |
| Lab外主动写入/父Git修改 | 未执行；对应字节检查另列 |

新公开报告不保存私人绝对路径、完整系统诊断或原始大日志。原始数据保持本地ignored，
新日志包也不stage。源码/公开摘要/补丁精确审核，SDK/Object/库/凭据禁止进入Git。
M10原始祖先含本地M9私人路径，不能直接推送整个原始历史来满足本轮隐私要求。
正常工具自动缓存/日志和模式扫描均有可观测边界，不宣称独立系统级零副作用审计。
