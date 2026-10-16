# 独立 KPI 审计和非部署链接

`run_m12_checks.py`只有显式 host/native/all 目标。固定19个编译单元：原Core9个、
lifecycle/shutdown、Native allocator/snapshot、M8/M10/M11契约探针、拒绝启动的
M11 kmod元数据探针，再加入真实锁适配和M12类型探针。device.cpp、plugin.cpp、
PSP/VM/ring硬件实现和上游Makefile均不进入allowlist。

现有Apple Clang以C++17、无异常、无RTTI、freestanding、4KiB栈帧限额、
KERNEL/KERNEL_EXTENSION、mkernel、fapple-kext、nostdinc++编译；x86无red-zone。
Host测试单独编译，保持Core限制但不把内核栈限额应用到STL测试程序。
子命令60s，CPU程序30s，原回归包装器600s；包装器子命令仍有独立超时。
串行编译，项目内TMP/cache，禁止生成Core Dump。

`m12_macho_audit.py`检查实际文件的CPU/type、有限load command白名单、section/
symbol/string/DYSYMTAB/relocation范围、macOS平台、EH/RTTI/全局构造器/TLS、
用户态导入、源文件/编译选项、重复强定义及符号提供方。ARM64合法
LC_LINKER_OPTIMIZATION_HINT作为有界linkedit数据核验；不会容忍未知命令。
它补充Apple nm/otool/lipo/dwarfdump，不是完整Mach-O加载器、重定位语义证明或安全认证。
符号及重定位完整表保存在忽略的local目录，公开摘要保留计数/哈希。

真实对象负样本10类：puts、未知导入、异常、RTTI、已导出但不属于此目标allowlist
的printf、全局构造器、项目自有符号提供方错误、实际对象字符串索引变异、重定位
索引变异、真实arm64对象用于x86。全部REJECTED。没有定义任何伪造Apple API。
异常对象先因EH section拒绝，Apple nm的真实符号再由同一runtime分类器确认。

`ld -kext -undefined error`对puts负样本仍返回0；独立审计拒绝它。
`printf`在参考导出表存在，但不是当前离线目标需要的KPI，所以归为
UNSUPPORTED_KERNEL_IMPORT，不能把它错称为不存在的Apple函数。
`_kmod_info`是原Apple KMOD宏生成的项目元数据，不是伪造Apple实现；只允许固定探针提供。

| 检查 | 结果 |
|---|---|
| 双架构19个内核对象/Apple ld-r/对象格式 | PASS |
| 内部模块依赖 | 全部已在组合对象解析 |
| 剩余导入 | x86_64 13，arm64 12；全部匹配对应源码导出参考 |
| x86 MH_KEXT_BUNDLE构造 | PASS；13个导入仍保留 |
| 匹配SDK15/真实目标二进制/完整目标链接闭合 | BLOCKED/UNVERIFIED |
| Bundle、签名、安装、加载、Kernel/GPU Runtime | NOT RUN |

完整mangled spelling、demangle、调用者、类型、参数宽度、对应架构导出文件/hash和
每个未验证项见reports/m12/kpi-details.json。IOMallocAligned的参考是
`_IOMallocAligned:_IOMallocAligned_external`；__bzero使用实际`___bzero`拼写。
IOService vtable是数据导入，不是“同名函数可以调用”的证明。
没有把KPI源码来源直接写成真实OSBundleLibraries版本或完成目标加载解析。

复现需要现有合法Apple工具和已审核的固定参考JSON；runner不自动取得它们。
以项目内保存的raw命令为准确复现依据，公开commands.json使用PROJECT_ROOT/
SDK_ROOT/PYTHON_EXECUTABLE标签。`m12_abi_reference.py`随后检查同一批编译头哈希，
进行源码文本比较和当前SDK真实layout数据整理。
