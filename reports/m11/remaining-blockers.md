# M11 剩余阻碍与M12入口

1. 对应macOS15.0的合法Apple SDK/真实x86内核KPI链接输入缺失。当前27头的vtable
   偏移不能替代15目标ABI，SDK匹配BLOCKED；公开XNU源码导出不是二进制验证。
2. 已获得真正独立MH_KEXT_BUNDLE静态文件，但八个外部导入仍保留；linker甚至接受
   `_puts`负样本。可信结果是文件构造/独立参考审查，不是完整目标内核链接闭合。
3. IOService是不可实例化静态探针；真实OSObject owner引用、内核workloop/gate/线程、
   停止/延迟终止及最后release/free没有运行或生产集成。
4. NativeOwnerStorage长期存储契约已编译；实际OSData/Buffer retain/release、prepare/
   complete失败恢复、DMA/映射/物理资源等NOT RUN。缓存裸指针的撤销需consumer协议。
5. GenerationClock需长期唯一domain与caller serialization，不能当安全认证；四次清理
   失败后保留资源，需要有条件恢复/隔离策略，不得无限重试或带borrower物理释放。
6. 发布branch准备且独立测试完成，推送仍需用户明确批准。原私人M9/M10提交不应直接
   推送。新的M11源码未来发布也需从干净历史导出并重新审查，不继承私人祖先。
7. x86程序/Rosetta、Windows、CMake运行NOT RUN，不能用arm64运行代替。
8. Discovery capture、真实gfx1200 ELF/固件/显存/显示引擎、PCI绑定、IRQ/DMA、
   DP/HDMI/WindowServer/Metal/Vulkan全部未验证；基础显示所需的实际硬件协议与
   OS图形栈整合仍缺。任何真实GPU/Kext运行与PC系统/引导操作须新阶段独立授权。

M12纯CPU优先：固定匹配SDK/目标内核参考（获取前另行批准）、真实vtable与导出比对、
补服务引用与shutdown owner集成、更多确定性失败/取消/借用恢复协议、离线ABI负样本。
已有非部署文件可作为工程起点；尚不具备可信的目标可加载/可部署驱动结果。
