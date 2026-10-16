# IOService ABI26

真实SDK26.5独立layout探针测量两架构：OSObject16、OSMetaClass40、
IORegistryEntry40、IOService136字节；各align8。继承链仍为
OSMetaClassBase→OSObject→IORegistryEntry→IOService。
探针不可实例化，不注册metaclass，排除生产链接allowlist。

实际vtable dump的free index20、init(OSDictionary*)75、will/didTerminate130/131、
start/stop186/187、open/close188/189、terminate194；偏移从ZTV符号起算，
不等于直接从对象vptr起算。未把测量偏移硬编码到驱动。

固定26.5源码与SDK26.5的IOService/RegistryEntry/OSObject/OSMetaClass词法virtual
声明序列分别108/72/10/37且相同；文本/宏投影差异仍有记录。
M12的SDK27三类尺寸可作历史对照，macOS15原二进制布局仍未知。
源码文字、同尺寸和符号名都不能证明目标内核vtable/构造析构ABI。

既有真实Native init/stop/free/retain/release/锁探针已用SDK26.5重编译。
没有OSDefineMetaClass、registerService、真实provider、PCI匹配或内核方法运行。
生产Publisher必须持Owner/锁的实际引用，停止回调来源、drain waiter和Ticket，
才允许最后release/free；Host mutex不能证明这个内核流程正确。
本轮修复ScopedInput::length在检查前写入输入别名，旧M12代码实际被新断言检出。
Gate/NativeOwner的真实运行与waiter drain仍KERNEL_RUNTIME_UNVERIFIED。
