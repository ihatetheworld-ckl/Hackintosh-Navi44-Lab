# M7 Darwin Adapter：实际接口与未验证源码

## 已有代码

platform/contract.hpp：显式分配/释放、结果日志、CPU Snapshot 借用、Lease。
host/platform_mock.hpp：固定 Node 数组、失败注入、分配/释放/日志计数；已在 Windows 运行测试。
platform/darwin_contract.hpp：不含 IOKit 的 AdapterDraft；硬件初始化恒 false。
platform/darwin_native.hpp/.cpp：真实 IOKit include、IOMallocAligned / IOFreeAligned、
IOLog 与 IOReturn 映射的静态草案；Windows 构建明确排除它们。
文件在非 Apple 或非 KERNEL 目标下显式 #error，不提供假的 Apple 类型。

## Kernel 生命周期契约

未来分配器最大 64 KiB、alignment 最大 4096。Lease 记录分配长度并使用匹配释放。
必须在可阻塞线程上下文调用，不能处于中断或 simple lock 临界区。
日志只输出内部 token / 错误码 / 输入 offset；不输出 PCI 物理地址、凭据或输入内容。
分配失败映射预算错误，日志不能成为 panic；未知验证错误映射参数错误。
这些映射是否符合目标 SDK 的 IOReturn、整数宽度、符号导出，需要真实编译确认。

重要未完成项：真实分配器必须明确提供 Node 数组对象生命周期。
Host Mock 自身持有活的 Node 数组；原始 IOMalloc 字节与 C++17 对象构造不能仅凭指针转换认为已解决。
首次 macOS 集成应采用目标 Kernel SDK 支持的 placement construction/对应释放，
或采用显式 typed-scratch 回调；同时验证错误与 teardown 路径。这是当前草案的阻碍。

输入缓冲必须由实际 OSData / IOMemoryDescriptor 的 retain/释放或独立拷贝保护，
但本轮没有实现对象包装、IOService probe/start/stop、IOPCIDevice 或 UserClient。
CPU Snapshot 接口不能自动升级为设备资源接口。
不新增资源探测、GPU 启动权限或安全开关。

## 证据与构建边界

Apple [IOLib.h](https://github.com/apple-oss-distributions/xnu/blob/main/iokit/IOKit/IOLib.h)
提供真实分配/释放及日志声明，并说明线程上下文限制（公开源码，2026-10-14 阅读，E1/E2）。
Lilu 固定 [kern_util.hpp](https://github.com/acidanthera/Lilu/blob/0515f40b7f2a096adc85e832a4c6104fbd07f936/Lilu/Headers/kern_util.hpp)
提供内核日志与 allocator 包装（E2）。本轮没有接入或调用这些第三方运行库。

Darwin native compile = NOT RUN；内核 ABI、符号解析、kext 链接及加载 = NOT RUN。
Host contract PASS 只证明纯 C++ callback 契约及模拟资源行为。
