# M11 并发证据边界

同步仍通过现有AccessOps/ExecutionOps注入。Host ThreadGate使用std::mutex/TLS，
禁止同线程嵌套gate和模拟中断上下文。SnapshotOwner/ShutdownBarrier回调有重入拒绝。
内核锁/工作循环没有在用户态执行，bool状态也不是内核锁。

锁顺序：先生命周期gate，操作资源状态；离开gate之后才持Host通知mutex或等待。
不在gate下等待drain、join或condition_variable。模型ReferenceOps callback不得阻塞等待
另一个需要gate的线程；Native分配还需合法可睡眠线程上下文，这部分尚UNVERIFIED。

M11并发为两worker各160次，总320次。通知协议保证两张ticket在stop时仍未归还，
然后在关闭后归还；其余318次新获取被拒绝。等待各2秒，外层用户程序30秒。
最初版本在快机器上可能320次全拒绝；已经补同步点，最终普通/ASan/TSan都实际
acquired=2、denied=318、errors=0，不用全拒绝冒充交叉生命周期覆盖。
M10旧240次worker及shutdown borrower继续作为回归，次数不累积到M11新增行为。

59项M11行为、400组有限初始化故障和上述线程协议在普通/ASan+UBSan/TSan实际通过。
没有无限fuzz。TSan的证明范围是已插桩的Host ownership/gate路径；旧不可变parser在
TSan生命周期链接中没有插桩，真实IOKit线程、OSObject、设备与内核内存模型均UNVERIFIED。
ASan leak detection关闭，leak NOT VERIFIED；源码没有假定这些结果授权硬件能力提升。
