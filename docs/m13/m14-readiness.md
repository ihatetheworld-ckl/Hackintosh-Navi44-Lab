# M14 的具体入口

已解决本轮SDK目标不匹配：真实SDK26.5、两架构22对象、独立导入/目标版本策略、
部分链接和x86静态Kext文件构造均有证据。仍没有目标内核二进制/KDK，
TARGET_ABI_CLOSURE=BLOCKED、LOADABLE_KEXT=UNVERIFIED。

最有价值的纯CPU后续：固定实际目标build后对合法KDK做x86符号/类布局比对；
完善Publisher引用/回调取消/锁waiter drain；继续有依据的DisplayID时序块解析；
将Scope消费者接入数据解析；扩展BO/VM/fence纯模型和跨task wire协议。

获取KDK须先核实官方版本/build、文件名、大小、SHA、许可和项目内离线处理方式，
再独立批准；不能安装pkg或使用目标之外内核来证明兼容。
当前26.5是静态基线，不预先决定未来安装26.5还是更新的26.x。

实际Navi44显示还缺数据来源、DCN/DMUB/PHY/固件/时钟、内存/IRQ/队列及OS图形栈。
GPU读取、Windows/SSD/EFI、Kext运行、训练/scanout/reset都需新的独立授权和恢复计划。
唯一显卡且无核显的黑屏风险尚不可接受，本轮不探索这些操作。
M13结束后停止，不自动开始M14。
