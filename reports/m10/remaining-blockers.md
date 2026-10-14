# M10 剩余阻碍

1. M9发布仍需用户独立批准19文件脱敏树及正常快照策略；原M9已提交，不能直接推送其
   私人路径祖先。M10当前基于原M9，未来发布同样需隐私历史策略，不能以删除当前文件规避。
2. 未确定目标Intel macOS/XNU与合法完整Kernel链接输入；公开导出表与SDK声明不是实际
   内核导出/vtable匹配证据。所有外部导入仍requires_real_kernel_link。
3. Full Kext Link、Bundle、入口/IOService/Info.plist、签名/加载均NOT RUN。
4. 真内核gate、线程上下文/锁顺序、可阻塞分配上下文、stop/drain/free与wrapper存储强引用
   未实现或运行。NodePool/Lease依赖caller串行化，generation须唯一发行。
5. Native OSData/Buffer真实引用和恢复未执行；prepare/complete只验证CPU模型。
   完成失败时如何在真实内核恢复/取消，任务权限/映射/物理指针撤销未验证。
6. Host Mutex/TSan/ASan不能证明Kernel并发或OSObject内存安全；leak detection NOT VERIFIED。
7. 不能在物理销毁后调用C++对象，也不能由逻辑ticket抹去旧裸指针；需要真实owner存活
   与consumer协议，未来UserClient权限不能把generation当授权凭据。
8. x86_64程序运行NOT RUN；未确认/安装Rosetta。Windows Regression及CMake执行NOT RUN。
9. 真Discovery/ROM/gfx1200Shader、PCI/MMIO/firmware/GPU/显示/Vulkan/Metal全未验证，
   不属于本阶段成熟度。下阶段依旧不得自动进入硬件/部署。
