# IOService ABI：当前测量与目标未知

独立的`m12_ioservice_layout.cpp`使用真正SDK27类和Apple Clang的record/vtable
layout dump。类含纯虚函数，未实例化、未注册metaclass，退出生产链接allowlist。
sizeof常量从实际Mach-O数据段读取；没有自制头文件或手写目标布局。

两个架构当前测量相同：OSObject16、IORegistryEntry40、IOService136字节；
IOService align8。真实继承链是OSMetaClassBase→OSObject→IORegistryEntry→IOService。
这些数字只描述当前SDK及当前编译宏，不代表目标15二进制。

| 当前SDK table index | 方法 | 从ZTV符号起算字节 |
|---|---|---|
| 20 | free | 160 |
| 75 | init(OSDictionary*)；探针override | 600 |
| 128 | init(IORegistryEntry*, plane) | 1024 |
| 130 / 131 | willTerminate / didTerminate | 1040 / 1048 |
| 186 / 187 | start / stop | 1488 / 1496 |
| 188 / 189 | open / close | 1504 / 1512 |
| 194 | terminate | 1552 |

Apple-kext qualified superclass调用的实际disassembly与600/1496/1040/1048一致。
这里是**从ZTV符号起算**，不能直接当作对象vptr的偏移。数字只存报告，未硬编码进源码。
目标15所有槽位仍UNVERIFIED。

本轮实际读取固定XNU15 IOService/IORegistryEntry/OSObject/OSMetaClass及IOLocks文本，
与SDK27逐文件hash和去注释声明序列比较。IOService108、IORegistryEntry72、
OSObject10个词法virtual声明的序列相同，但五个文件全部字节不同。
OSMetaClass37个词法声明中有override标记等文本变化。该扫描包含未预处理的
条件分支及宏，不能据计数计算目标vtable；即使所有声明文字相同也不足以确认ABI。
APPLE_KEXT_VTABLE_PADDING、KERNEL_PRIVATE、OSPtr模式及宏展开必须在匹配SDK下复核。

现有M11静态IOService契约保留init/start/stop/free/open/close/termination类型检查，
start/open拒绝，类不可实例化，free仅是受保护编译接口。M12加入真实锁及Owner
consume/stop的RAII编译调用，未将其接到kmod入口或真实服务。
生产IOService仍需持有Owner/lock的实际引用：先停止新回调并撤销获取，异步drain，
等所有borrower/scratch/waiter归还后才允许最后release/free。
`free()`不能把“等待borrower”当成可在最后引用释放后重试的机制。
will/didTerminate的defer与provider关系必须在真实版本下设计并独立授权验证。
没有OSDefineMetaClass、registerService、IOPCIMatch、PCI绑定或Registry修改。
