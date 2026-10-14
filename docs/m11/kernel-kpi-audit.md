# M11 KPI 与真实ABI边界

x86_64部分对象及独立MH_KEXT_BUNDLE保留八个导入：

| 实际Mach-O拼写 | 来源/静态要求 |
|---|---|
| `_IOMallocAligned` | IOKit；公开vm_size_t/vm_offset_t原型，导出表外部实现别名 |
| `_IOFreeAligned` | IOKit；address/原始长度与allocator配对 |
| `_IOLog` | IOKit；const char*可变参数，静态诊断token |
| `_memcpy` | Libkern；CPU复制/长度边界 |
| `___bzero` | Libkern；x86编译器产生的零初始化 |
| `__ZN6OSData9withBytesEPKvj` | Libkern；raw OSData*，const void*/unsigned int工厂 |
| `__ZN24IOBufferMemoryDescriptor9withBytesEPKvmjb` | IOKit.x86_64；vm_size_t/IODirection/bool工厂 |
| `__ZTV9IOService` | IOKit；真实C++ superclass vtable引用 |

固定macOS15.0 XNU的公共及x86导出表逐项存在；实际行/文件SHA、使用者、内部提供方
在symbol-audit.json。分类 **VERIFIED_EXPORT_REFERENCE** 只表示公开源参考，
实际目标内核二进制、vtable布局与KPI依赖版本仍 **UNVERIFIED**。
没有把架构专用x86导出表当作arm64证据；arm64七个外部项保留UNRESOLVED_ABI_REQUIREMENT。

真实27 SDK通过allocator、logger、OSData/Buffer工厂函数指针类型与整数宽度断言。
IOService原型在固定15公开源也可查到，但Apple Kext ABI对super调用生成vtable索引：
本次x86反汇编init偏移0x258、stop0x5d8、will/didTerminate0x410/0x418。
这些是 **当前SDK** 的代码证据，不能推断15内核槽位完全相同。

最初一个out-of-line虚函数导致整个派生vtable及额外C++运行时导入；已改为全部
内联的抽象类声明和有界接口探针。没有放宽EH/RTTI/Host运行时策略，也没有提供
Apple API Stub。最终Core/Native对象不含策略禁止的依赖。

`ld -kext -undefined error`实际exit0，但会保留外部导入，并警告该undefined选项弃用。
真实Host `_puts`负样本也得到linker exit0，独立符号审查正确拒绝它。
因此链接器exit不是ABI/KPI认证；普通目标在未知导入出现时停止对应链接步骤。
