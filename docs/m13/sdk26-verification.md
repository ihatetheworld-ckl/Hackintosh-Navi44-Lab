# 真实 SDK26 选择与隔离

已读取CLT `MacOSX26.5.sdk` 的SDKSettings/SystemVersion及真实Kernel.framework。
Version26.5、SDK build25F70，IOLib/IOLocks/IOService/OSObject/OSData/
IOBufferMemoryDescriptor/OSMetaClass/IORegistryEntry均存在。Xcode默认SDK仍27，
所以新runner要求显式--sdk；不调用默认SDK来构建正常对象。

m13_target.py拒绝版本/metadata不符、Kernel头越界、SDK27头、错误对象SDK/minos
标签、旧XNU15参考或内容哈希变化。源码导出固定到单一26.5 commit。
Compiler内建头来自已安装Clang资源目录，Host libc++来自已安装Apple工具链，
分别记录类别；它们不伪装成SDK26或Native C++ runtime。

每条正常Clang编译命令输出真实.d依赖，记录Source SHA、架构、isysroot、Kernel
root、部署目标、选项、产物SHA。145组依赖集合、1223个唯一源码/头文件的hash
见header-dependencies.json，完整关系表留ignored local。正常编译SDK混用发现0。
隔离SDK27/旧部署目标负样本不计入该正常集合，legacy M12基线也独立保存。

Native编译C++17、no exceptions/RTTI、mkernel/fapple-kext、nostdinc++、4KiB栈帧
限制，x86禁red-zone；只编译明确22单元allowlist。Host测试主程序不受内核栈限制。
所有TMP/cache在Lab；子命令有超时，串行编译，CPU线程有界。

SDK声明及对象layout验证PASS；对应系统内核二进制、KDK和可加载性未验证。
