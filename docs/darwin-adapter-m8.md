# M8 Darwin Adapter contract

沿用MemoryOps / LogOps / SnapshotOps / Lease；新增ScratchOps / ExecutionOps，
SnapshotOps增加成对release。旧raw MemoryOps继续只服务原始字节；解析器不再将raw分配cast为Node。

Host Mock从对齐uint8_t数组改为真正的Node[512]，修正M7未解决的C++对象生命周期问题。
NodePool也直接持有构造好的Node数组；nativeScratchOps只引用调用方构造的pool，
不依赖伪造的placement-new/SDK，不暗中分配或操作设备。
Kernel pool应随长期owner对象存活、放在堆/owner成员中，不能放入kernel栈。

validateSnapshot顺序：ExecutionOps.enter → borrow input → acquire live Nodes →
Core validate → release Nodes → release input → log → ExecutionOps.leave。
失败/无scratch/解析拒绝均按RAII配对释放；缺失context或lifetime callback时拒绝。
Mock测试了parser失败、资源不足、错误上下文、重入与missing release。
Mock的inCall/busy是串行模拟，不是原子锁。NodePool不是thread-safe，
真实Darwin adapter必须提供线程上下文与正确的serialization/teardown，不能把bool当内核锁。

日志仅内部静态token/输入offset，不输出物理地址、serial或payload。
callbacks是可信adapter契约：不能抛异常、访问硬件或在中断中调用可阻塞分配/日志。
跨callback重入和异步销毁的真正kernel实现仍NOT RUN。
借用View副本不会自动失效；owner必须保持输入、context和callback lifetime。

只静态阅读：
[固定MacKernelSDK IOService.h](https://github.com/acidanthera/MacKernelSDK/blob/05094e5e88cec7caedbfb35e8449ed0db94bf95b/Headers/IOKit/IOService.h)
的probe/start/stop/open/close/handleOpen及arbitration语义；
[Apple OSObject](https://github.com/apple-oss-distributions/xnu/blob/main/libkern/libkern/c++/OSObject.h)
的retain/release与并发限制；
[IOLib](https://github.com/apple-oss-distributions/xnu/blob/main/iokit/IOKit/IOLib.h)线程上下文要求。
这不等于实际IOService包装或引用计数已经接入。
pin IOLib/IOPCIDevice部分网页抓取失败；未下载SDK替代或伪造类型。
Darwin native build、kext link/load、PCI binding均NOT RUN。
