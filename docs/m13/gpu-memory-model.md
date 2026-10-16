# CPU 地址、Fence 与撤销模型

ResourceModel只保存整数地址区间/预算/状态，不分配内存、不映射VRAM/BAR、
不调用GPU或内核API。4096是CPU模拟页单位，不是推断的GPU页大小。
固定8个条目，必须持既有AccessOps gate，GenerationClock长期单调发行id。
ModelHandle含实例身份/slot/generation，ModelFence另含serial，均不是安全凭据。

reserve检查对齐、整数回绕、窗口、预算、区间重叠、容量、输出句柄占用；失败不
丢弃现有句柄。queueModel仅推进模拟Pending，completeModel不接受旧serial或跨owner。
deadline是调用者提供的逻辑tick，不使用真实GPU计时器。

Pending→Completed；超时→TimedOut+Revoked。Stop/ResetModel拒绝新请求并撤销，
但不会把Pending/TimedOut当作已停止执行。必须显式acknowledgeCancellationModel
后才能release；这只是CPU模型确认，未来真实Backend必须提供独立硬件quiescence
证据。模型自身永不授权hardwareSubmission。

释放清空条目，地址重用取得新generation；重复释放、过期fence、跨owner均拒绝。
Stopped不可重新激活，重建对象须保持同一长期GenerationClock，避免ABA。
模型没有生产级task权限、真实GPU页表、VRAM预算、DMA缓存一致性、IRQ或GPU reset。
SnapshotOwner仍负责真实数据借用；没有将普通Host内存冒充IOKit对象。
