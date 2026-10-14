# M11 IOService接口契约

tests/unit/m11_native_compile.cpp采用真实IOService继承/override原型，类抽象且没有
OSDefineMetaClass注册。start/open始终拒绝；不连接provider、不访问Registry/PCI。
init/stop/willTerminate/didTerminate只在编译探针中检查super接口，均不运行。
free受protected限制，只表示最后引用释放时的回调，不允许外部probe任意调用。

Apple [基类生命周期](https://developer.apple.com/library/archive/documentation/DeviceDrivers/Conceptual/IOKitFundamentals/BaseClasses/BaseClasses.html)
规定初始化与清理的super调用顺序；
[移除流程](https://developer.apple.com/library/archive/documentation/DeviceDrivers/Conceptual/IOKitFundamentals/DeviceRemoval/DeviceRemoval.html)
区分失效、等待请求、stop/detach和最终释放，didTerminate可延迟终止。
这些是Kernel IOKit文档，不混用DriverKit Start/Stop的不同API。

原probe在任意外部引用上直接调用free，Apple分析器实际报osx.cocoa.RetainCount。
已移除外部free调用，并限制可见性，真正重新分析为零warning；未禁用checker。
生产实现必须由最后release触发free，不能用readyToFree许可去直接free一个仍有OSObject
引用的对象。readyToFree只保护内部资源/存储，OSObject引用是另一层约束。

NativeOwnerStorage将NativeSnapshot、ShutdownBarrier和NodePool放在caller长期拥有的
存储中。初始化失败执行关闭；Snapshot工厂引用仍按M10真实API配对，OSData/Buffer不
prepare/complete、映射或DMA。scratch新获取要求ACTIVE且持gate，归还允许关闭阶段；
NodePool非idle时readyToFree拒绝物理释放。没有把Host普通内存称为真实内核对象。

真实服务owner强引用、workloop/command gate、普通线程/中断区分及终止回调调度尚未
集成/执行。没有可运行服务类或设备匹配。IOService init/start/stop/free/open/close/
terminate/willTerminate/didTerminate运行全部NOT RUN。
