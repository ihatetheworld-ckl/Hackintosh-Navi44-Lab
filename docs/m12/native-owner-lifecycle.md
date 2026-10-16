# Owner、受控输入和真实锁边界

NativeOwnerStorage现在显式initialize→Initialized→start→Active；初始化不会自动
激活请求。ShutdownBarrier保留旧Core调用方从Created直接start的兼容路径，Native
外部接口只能走显式初始化。Stopping→Draining→Released，以及Failed保持原清理
顺序和最多4轮失败重试；未归还Ticket不消耗错误重试预算。禁止Released重新激活。

| 资源 | 引用/使用规则 | 停止与释放 |
|---|---|---|
| OSData/IOBufferMemoryDescriptor | 原raw factory count1；SnapshotOwner再retain；创建方drop初始引用 | 所有借用归还后release Owner引用；未在Host调用内核方法 |
| NativeSnapshot | 私有内核对象指针；仅CPU DataCopy/BufferCopy、kIODirectionNone | 不prepare/map/DMA；存储必须长于所有消费者 |
| SnapshotOwner | 一个Owner引用，最多8个有identity/generation/serial/slot的Ticket | Stop/Revoke后不再读/借；旧Ticket仍可归还；complete失败保留引用 |
| ScopedInput | 回调期间不可复制/移动/外部销毁；没有View/data指针getter | 自动Ticket即使callback错误也归还；拒绝回调递归/close/revoke |
| NativeOwnerStorage | caller在长期存储创建；去除公开lifetime getter/raw Ticket路径 | readyToFree要求Barrier释放且NodePool空闲；没有擅自从析构执行内核清理 |
| NodePool | caller持同一个gate；真实Node对象，按准确ptr/count归还 | 停止后禁止新获取，允许合法归还；scratch未归还禁止物理销毁 |
| BorrowedKernelGate | publisher拥有IORecursiveLock及adapter；本类不分配/释放锁 | 必须移除回调源并drain waiter，才能销毁锁/adapter/owner |
| GenerationClock | 长期domain、同一gate、单调非零且不回绕 | 地址重用必须取得新generation；不是认证Token |

ScopedInput只向合法caller目的内存复制有界字节，拒绝空指针、整数回绕、越界、
与任何原输入范围重叠。失败不改目的；byte原先在检查前清零的别名写入缺陷已修复。
真实旧实现被新增测试实际检出，日志与退出1保留。该接口不接受未经验证的用户态
指针；算术范围合法不证明内存已映射或可写。

`consume`的callback必须noexcept、有限、同步完成，并在整个作用域保持caller gate；
`withInput`保留显式Ticket义务。可信caller不得缓存ScopedInput引用。
C++无法阻止恶意消费者保存引用、强制转换或在callback后使用悬空引用。
旧兼容read/legacy SnapshotOps仍可给裸View；没有宣称逻辑撤销能让缓存指针物理失效。
复制出的普通CPU数据不再代表对原资源的授权。没有GPU Memory/VRAM对象。

BorrowedKernelGate实际调用IORecursiveLockLock/Unlock/HaveLock和ml上下文接口。
只在普通、interrupts enabled线程进入，拒绝同线程递归；调用方还须保证可睡眠、
未持spin lock、进入后不改变中断状态。API不能证明所有调用方上下文。
Lock ordering为外部发布/注册控制→资源gate→短小资源逻辑；callback不得取得反向
发布锁、等待会获取gate的worker或重入logger。Drain等待在gate之外。

Host使用自己的std::mutex/current-thread模拟，模拟interrupt布尔值只测试拒绝路径。
并发测试让stop发起于scope仍活跃时，然后观察串行清理和160次新请求拒绝。
测试协调condition_variable有2秒限额且其通知者不取得资源gate，不能照搬成内核
callback阻塞策略。ASan/UBSan/TSan只覆盖Host逻辑；真实锁、OSObject运行仍NOT RUN。
