# M13 入口条件

已有SDK27的双架构19对象、部分链接、x86 Kext类型文件与独立负样本审计，足以
继续离线工程。尚无目标15 ABI闭合或可加载Kext证据。

可继续CPU工作：扩大独立Mach-O策略负样本；把scope输入接入有界解析消费者；
设计服务发布者引用/回调取消/锁waiter drain；明确长期Generation domain、失败隔离、
BO/VM/fence纯模型；固定Navi44与Cobalt生产wire协议，不复用N48N版本假设。
Windows、CMake及x86 Host运行须在真实可用环境执行，当前不能推断通过。

目标ABI下一步须先获得独立SDK/KDK获取授权，取得合法匹配SDK15.0及准确系统build
对应x86_64内核/符号资料，验证class layout、宏、KPI版本及每个实际导入。
匹配SDK编译和二进制静态审计仍不等于加载认证。不能以公共XNU重新编出的内核或
SDK27混合头替代Apple实际目标二进制。

Navi44基础显示还缺真实Discovery/connector/IP实例、GOP状态、DCN/DMUB/PHY/HPD/
AUX和时钟协议、firmware契约、Framebuffer与macOS图形栈整合，以及完整资源停止恢复。
Vulkan/Metal更需VM/queues/fence/Shader/winsys和OS共享接口。

任何Kext加载/调试、GPU数据采集、PCI/MMIO/DMA/固件/显示/Windows/引导/磁盘操作
都需要新的独立授权与具体恢复条件。本阶段结束即停止，没有自动M13或硬件实验。
