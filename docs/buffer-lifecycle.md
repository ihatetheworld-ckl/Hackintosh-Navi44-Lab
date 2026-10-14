# M10 Buffer / Snapshot 生命周期

Host使用普通CPU数组与逻辑引用计数；真实Native使用Apple OSData/
IOBufferMemoryDescriptor类型，只做编译和部分链接。不存在GPU BO/VRAM。

NativeSnapshot::createCopy复制caller提供的有效immutable字节，限1..1MiB，
拒绝null、长度/地址溢出；caller须保证输入地址实际有效且复制期间不被修改。
OSData和Buffer工厂均产生独立副本，内部对象指针不对外提供。

真实公开SDK的OSPtr在未启用实验选项时是原始指针。
工厂返回初始引用1；SnapshotOwner.activate额外retain，然后显式release工厂引用。
初始化中途失败时配对释放这两个不同的引用义务。没有启用实验宏或虚构Apple类型。
公开raw ABI及descriptor长度宽度有真实编译断言。

Snapshot借用本身不额外retain每次ticket；owner强引用保护全部未归还tickets。
revoke/close后read清空View并拒绝，新borrow也拒绝；原持有者归还后才能释放对象。
实际IOKit retain/release没有在用户态执行；Host逻辑计数不是内核实测。

Apple规定prepare须由caller串行化，complete与已成功prepare配对。
本轮ReferenceOps支持这些状态：prepare失败不complete；complete失败保留引用和
prepared状态，不释放/重开，允许在合法gate下重试complete。600组失败注入实际运行。
来源：[prepare官方文档](https://developer.apple.com/documentation/kernel/iomemorydescriptor/1812845-prepare)，
及已安装SDK IOMemoryDescriptor/OSData头。

Native CPU副本路径不调用真实prepare/complete；没有DMA、物理段、映射、task权限
或用户任务地址访问。实际内核准备/完成、映射撤销、并发与停止仍UNVERIFIED。
逻辑撤销无法让已缓存的裸指针立即失效；所有consumer必须遵守ticket/gate契约。
已实现长度/地址范围检查不能证明任意裸指针实际指向有效内存。
