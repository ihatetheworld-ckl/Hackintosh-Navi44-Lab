# 安全边界：M6.5

项目内写源码和 CPU-only 测试获授权。没有系统、驱动、启动、安全策略或真实 GPU 实验授权。
Clang/LLD/runtime 仅便携解压到 lab；无安装器、注册表、全局 PATH 或管理员权限操作。
host source 列表只含解析、校验和测试；没有 device.cpp/plugin.cpp/IOKit、Vulkan、DX、OpenCL。
Navi44 不绑定；hardwareInitializationAllowed 恒 false；开发 Makefile 保持禁用。

测试用固定种子、有限输入（当前最大约1200 bytes）、单个顺序 probe、30 秒执行 timeout、60 秒编译 timeout。
没有声明额外的 OS Job 内存配额或专属 lab 沙箱；不穷举/无限 fuzz、不占用 GPU。
ASan/UBSan canary 是自有 CPU 进程的故意错误；仅用于验证检测器，非正常数据 PASS。
LeakSanitizer 未验证，detect_leaks=0；检测通过不证明全代码无内存漏洞。
系统/网络的正常日志缓存不能承诺物理零写入。项目没有执行磁盘/硬件访问审计，不能作绝对安全证明。
