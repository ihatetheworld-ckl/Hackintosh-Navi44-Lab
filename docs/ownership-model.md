# M10 Ownership Model

复用已有MemoryOps/Lease、SnapshotOps、ExecutionOps和NodePool，增加纯CPU
SnapshotOwner/ReferenceOps；没有第二套GPU或IOService框架。

| 资源 | Owner / borrower | 清理规则 |
|---|---|---|
| ReferenceOps资源 | 创建者初始引用；SnapshotOwner另持1个强引用 | activate retain成功后配对release；失败清理；所有tickets归还前不得释放 |
| SnapshotTicket | caller持有归还义务，最多8个 | generation/serial/slot核对；重复/外来票据拒绝；成功归还后清空 |
| View | immutable借用，依赖活跃ticket及执行gate | 每次read核查状态；失败清空out；不拥有或提升能力 |
| NodePool | 长生命周期caller构造真实Node数组 | 外部串行化；只接受本数组/准确数量归还，清空Node；错误归还不解锁 |
| MemoryOps Lease | 一个caller拥有一个分配 | 释放前清空状态，回调期间拒绝重入；重复close不再次释放 |
| NativeSnapshot wrapper | caller持有长期wrapper/gate/generation | readyToFree成立且全部tickets归还后才能实际销毁其存储 |

状态：CREATED→ACTIVE→CLOSING或REVOKED→RELEASED；初始化失败到FAILED，
只允许清理；complete失败也到FAILED并保留资源，成功重试complete后才release。
ACTIVE不允许重新activate，RELEASED不能重开。新的生命周期须创建新owner/generation。

所有owner操作必须在该AccessOps的gate已由普通线程持有时执行。
内部operation标记拒绝回调递归，不能替代锁。generation必须由可信caller唯一发行，
包括跨owner与存储地址复用；ticket不是UserClient权限或安全认证凭据。

Close是非阻塞shutdown请求：禁止新借用/读取，已有tickets仍需归还。
有未归还tickets时返回shutdown_pending并阻止readyToFree。最后归还执行
complete→release。重复close/revoke不重复释放。一次资源组中后续创建失败须逆序关闭
此前成功资源；本轮对两个资源的部分初始化失败做了真实CPU验证。

回调不得抛异常，release须在合法执行上下文完成且不失败。
Owner不在未知线程析构中擅自执行内核清理；caller必须落实stop/drain/free协议。
本阶段没有真实IOService stop/free、owner存储引用或generation发行器。
物理销毁后的C++对象不能合法调用方法；测试验证的是RELEASED状态拒绝重入，
不是让已销毁的内存变得安全。原始View缓存也无法被逻辑撤销自动抹除。
