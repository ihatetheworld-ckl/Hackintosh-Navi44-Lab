# 下一阶段就绪度

Windows host core已编译及离线测试；macOS构建NOT RUN，不能复用PE binary为kext。
IpDiscovery/CodeObj保持无IOKit、无allocation接口；offlinevalidation host层依赖STL/异常，
需要无异常错误返回/allocator或独立纯解析kernel适配后才能进kext。
新增IpEntry64不改变旧条目布局，但parser对象内部大小改变，所有macOS使用者需要重新构建。
上游Makefile可核对的目标是x86_64-apple-macos11.0、C++17、-mkernel/-fapple-kext、
-fno-exceptions/-fno-rtti、-nostdinc/-nostdlib；host的STL/异常无法直接用于此目标。
上游submodule pins：Lilu 0515f40b7f2a096adc85e832a4c6104fbd07f936，
MacKernelSDK 05094e5e88cec7caedbfb35e8449ed0db94bf95b；本轮没有递归获取/运行。
具体Xcode/SDK版本尚未验证，不能由Windows Clang版本推出；需要合法Apple SDK和x86_64内核目标。
没有伪造头文件，也不能将Windows PE程序当Mach-O kext。
代码配置仍参考上游macOS11 API，未证明可跨Sequoia/Tahoe；OpenCore只是未来注入条件，不是本轮产物。
签名/加载与安全策略必须独立决定，本轮不改变系统保护或生成可加载kext。
真实显示：板卡数据/连接器/固件/profile、继承GOP、受控模式及恢复计划，需授权。
提交：VM/BO/fence/IP固件和超时；Vulkan：真topology/ABI/RADV；Metal：完整资源/shader/系统接入。
