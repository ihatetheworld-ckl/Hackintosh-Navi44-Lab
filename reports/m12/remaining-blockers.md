# M12 剩余阻碍

1. **BLOCKED**：合法macOS15.0 SDK、准确目标系统build对应x86_64内核/KDK与KPI
   链接材料缺失。没有下载/安装授权；SDK27结果不能替代匹配头、导出或C++类布局。
2. **UNVERIFIED**：13个x86导入虽全部匹配固定XNU源码导出参考，目标二进制导出、
   版本/宏/调用布局/IOService vtable仍未确认。MH_KEXT_BUNDLE构造不是完整目标闭合。
3. **NOT RUN**：真实IOService、OSObject retain/release、内核锁/thread、Buffer
   prepare/complete/map/DMA运行。已有Native编译接口和CPU模型，缺生产publisher引用、
   取消回调与waiter drain及最后release/free整合。
4. scope仅限制合法接口逃逸；不能阻止恶意C++缓存引用/强制转换。旧裸View接口仍因
   跨平台兼容保留。物理资源销毁、Generation长期domain和错误隔离需调用者正确实现。
5. **NOT RUN**：Windows、x86用户态运行、CMake配置执行；无对应运行环境/现有CMake。
   没有安装Rosetta或工具，也没有连接Windows。
6. **NOT RUN**：GPU/PCI/MMIO/DMA/firmware/VRAM/queue/IRQ/显示/Vulkan/Metal/WindowServer。
   真实Navi44 Discovery/connector/DCN/DMUB及gfx1200数据缺失，Navi48假设不能替代。
7. M9–M11干净发布已获独立批准并推送；M12尚未获推送授权，原私人祖先不得直接推送。
   发布M12需要从干净发布历史精确导出并再审查/测试/确认。

无需这些授权即可继续的后续CPU工程见docs/m12/m13-readiness.md。本轮结束后停止。
