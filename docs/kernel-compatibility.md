# M7 内核兼容性与真实 macOS 构建路线

## Windows 已验证

四个 Core translation unit 用 C++17、-fno-exceptions、-fno-rtti、-ffreestanding、
-Wall -Wextra -Werror、-Wframe-larger-than=4096 编译。
llvm-nm 审查未定义符号，没有发现 throw/RTTI/unwind/STL/new 符号依赖。
仍有 memcpy/memset 和内部 CodeObj / IpDiscovery 引用，未来须由 libkern/对应 Core 目标正确解析。
freestanding flag 及单函数栈警告不证明完全 freestanding、递归总栈安全或 Apple 内核 ABI。
Windows x86_64 PE/COFF 产物没有被当作 Mach-O kext。

## 模块分类

| 模块 | Windows CPU 验证 | 真 macOS 构建需求 | 实机需求 |
|---|---|---|---|
| ASIC / Discovery / metadata / ELF / package / N44I | 已运行 | Apple Clang 与内核头确认布局/符号 | 真实只读样本确认语义 |
| Host adapter / Python / probe | 已运行 | 不放入 kext | 无 |
| Platform contract / Host Mock | 已运行 | 真实分配、对象构造和输入生命周期 | 无 GPU 的适配验证先行 |
| darwin_native | 未运行 | 合法 Kernel SDK / IOLib / IOReturn | 独立 CPU 测试后才考虑加载 |
| plugin / device / DCN / PSP / VM / queue | 本轮未构建 | Lilu / MacKernelSDK / 目标系统 API | 必须独立授权 GPU 实验 |
| Cobalt / RADV / Metal | 静态阅读 | Mesa、合法用户态/内核 SDK、ABI 集成 | 必须验证 gfx1200 与资源所有者 |

## 固定参考

AMDRadeonRDNA4 49f7f20c00dd154384418078f8a09e79c400a06a 的 Makefile 被静态阅读，未执行。
可见 x86_64-apple-macos11.0、C++17、-mkernel、-fapple-kext、-nostdinc/-nostdlib、
禁异常/RTTI 的构建策略；不能直接在 Windows 转换成生产构建。
Lilu pin 0515f40b7f2a096adc85e832a4c6104fbd07f936；
MacKernelSDK pin 05094e5e88cec7caedbfb35e8449ed0db94bf95b。
本轮未递归获取 submodule，没有运行其构建脚本或初始化 hooks。

## 未来依赖图与清单

~~~mermaid
flowchart TD
    A[合法 Apple macOS SDK / Kernel SDK / Xcode] --> B[Apple Clang x86_64 target]
    P[Core explicit source allowlist] --> B
    K[审核后的 MacKernelSDK / libkern] --> B
    B --> C[真正 Mach-O Core object check]
    D[Darwin allocator / typed scratch / lifetime] --> C
    C --> E[CPU-only macOS fixture runner]
    L[审核后的 Lilu / target kext project] --> F[未来 kext link / symbol validation]
    E --> F
    F --> G[另行授权后才可加载或绑定硬件]
~~~

1. 在用户另外授权的真实 macOS 环境记录 Xcode、Apple Clang、合法 SDK 精确版本。
2. 首先只编译 Core allowlist，禁异常/RTTI；以实际头文件验证布局和整数转换。
3. 解决 C++17 Node lifetime、分配器对应释放、retain/teardown 与 kernel stack 预算。
4. 运行 CPU fixtures；审查 Mach-O 未定义符号、libkern 引用、静态初始化与对象析构。
5. 独立设计与审核 kext target、Info.plist、OSBundleLibraries；不复制 Windows host adapter。
6. 单独选择 macOS 11 ABI 实验起点。Sequoia/Tahoe 等跨版本需逐版本编译/测试，当前 NOT RUN。
7. 加载/安全策略/签名、Boot、任何 GPU 绑定均属于额外授权阶段。

本轮 CMakeLists 更新只经过静态审查；实际构建使用 Python 调用便携 Clang。
CMake configure/build = NOT RUN，MSVC 分支 = NOT RUN。OpenCore 的安装注入与版本适配未开展。
