# M10 并发与关闭契约

普通线程且该owner执行gate已持有，是retain、read、borrow、归还、close、complete、
release的前提。中断上下文、未持有gate、错误gate或对象回调重入立即拒绝。
NativeSnapshot复制调用同样先检查owner上下文，不在Host执行内核对象。

Host ThreadGate使用真实用户态std::mutex及thread_local持有者身份。
不是原M9的bool，也不是IOKit内核锁。GateScope负责配对enter/leave。
每个线程最多持有一个此类gate，跨gate嵌套也拒绝，避免模型中的锁顺序循环。

模型锁顺序：owner gate→状态/引用/私有字节访问；不能在gate持有期间等待
其他borrower归还。close先置Closing/Revoked并返回pending，释放gate，
其他borrower再归还；最后归还在gate下完成清理。
日志重入由既有ExecutionOps入口拒绝；资源回调重入由owner operation拒绝。
释放前失效Lease指针，防止release回调再次close造成double release。

实际有界并发：两个worker共240次borrow/read/return，另一个borrower与shutdown
通过有2秒上限的condition-variable同步，覆盖关闭请求期间仍持ticket的路径。
worker接受/拒绝数随调度变化，但总数固定240；错误计数必须0，最终complete/release各1。
本轮TSan实际PASS，覆盖生命周期.cpp与Host同步Mock；不可并发的旧parser对象未做TSan插桩。

Kernel未实现真实工作循环/锁/thread-context识别，因此Kernel Thread Safety UNVERIFIED。
实际IOLib/OSObject API可能阻塞，未来gate必须适用于普通可阻塞线程，不能持简单/自旋锁
调用这些API。原NodePool/Lease继续要求caller串行化，不能单独跨线程共享。
真正IOService引用、stop/free屏障、用户任务撤销、锁顺序和取消需独立内核工程验证。
