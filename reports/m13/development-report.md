# M13 实际开发交付

状态COMPLETE_WITH_BLOCKERS。正式目标已迁移macOS26 Tahoe；使用真实SDK26.5
完成Core/Native编译、独立审查及CPU模型开发。目标二进制ABI仍缺材料，未运行Kext/GPU。

## A. 目标迁移

从实际核验的M12 `33e130f10ce24b840e16502a4bd6c618fd3eb824`建立
`m13/macos26-navi44`，没有从main开始。M12清单/执行hash、历史报告和许可证核验通过；
修改前独立复现M12 legacy基线，输出只到reports/m13/baseline，不覆盖原证据。
原基线的SDK27/minos15明确标作legacy，不能记作M13 Tahoe验证。

本轮静态基线选macOS26.5，CLT SDK26.5/SDK build25F70，真实Kernel.framework
头存在。Xcode27.0/27A266a、Apple Clang21.0.0/clang-2100.3.34.2、ld-27037.1、
Python3.14.5，Host是arm64 macOS27.0.1/26A434。Xcode默认SDK27没有用于正常M13对象。
config/m13-target.json、README、AGENTS、CMake及M13入口已更新，旧报告全部保留。

Apple macos-260对应xnu-12377.1.9已确认；macos-264对应12377.101.15；
macos-265分发commit83390100289cedfe669c31a96c94326d31afa1ed的xnu gitlink
ac9718fb1af618d5ce8678d0dc6e8a58f252216f对应12377.121.6。
Darwin25为目标系列，实际目标kernel banner/build未读到。25F70是SDK元数据，
不替代目标内核证据。Apple更新列表另有26.7.1，本轮没有其SDK/XNU/KDK完整验证。
26.5是资料/现有工具相匹配的静态研发选择，不是最终安装版本。

145次正常Clang命令有实际.d关系、Source/输入对象/Header集合/输出SHA，1223个
唯一源码/头文件分类核对。Kernel依赖只接受项目、明确SDK26和Apple compiler builtin；
Host libc++另列。正常SDK混用发现0。完整关系保留local，公开记录无SDK内容。

## B. Darwin ABI

真实SDK26.5各架构22个允许对象通过。OSObject16、OSMetaClass40、
IORegistryEntry40、IOService136字节，各align8。真实layout探针和vtable dump独立于
生产链接；无实例/metaclass注册。init/stop/will/didTerminate等实际槽位已记录，
没有硬编码偏移。26.5公开类头与SDK对应词法virtual序列一致，但宏投影和目标二进制
仍未验证；相同文本/尺寸不证明真实目标vtable兼容。

x86_64剩余13个预期导入，arm64少___bzero共12个：

```
_IOFreeAligned
_IOLog
_IOMallocAligned
_IORecursiveLockHaveLock
_IORecursiveLockLock
_IORecursiveLockUnlock
__ZN24IOBufferMemoryDescriptor9withBytesEPKvmjb
__ZN6OSData9withBytesEPKvj
__ZTV9IOService
___bzero
_memcpy
_ml_at_interrupt_context
_ml_get_interrupts_enabled
```

内部依赖均解析，正常未知/不支持/Host/EH/RTTI导入0。
每项拼写/demangle/调用者/参数/头来源及SOURCE_DECLARED、SDK_DECLARED、
REFERENCE_EXPORTED与目标二进制/ABI的UNVERIFIED状态分列于kpi-details.json。
未定位的内存函数直接公开声明和编译器生成___bzero不假称已验证普通同名原型；
SDK string.h的memcpy/bzero声明及实际导出拼写另有依据。
没有取得匹配KDK/目标内核，TARGET_BINARY_VERIFIED和TARGET_ABI_VERIFIED不标PASS。

## C. 编译与链接

| 验收项 | 结果 |
|---|---|
| OBJECT_COMPILE | arm64/x86_64各22单元PASS |
| PARTIAL_LINK | 双架构Apple ld-r PASS |
| MACHO_KEXT_CONSTRUCTION | x86_64独立MH_KEXT_BUNDLE PASS |
| SDK26_ABI_AUDIT | 真实声明、类型、对象layout及目标标签PASS |
| KPI源码参考审计 | 固定26.5相应架构导出表PASS |
| TARGET_BINARY_KPI_AUDIT / TARGET_ABI_CLOSURE | BLOCKED |
| LOADABLE_KEXT | UNVERIFIED |
| Bundle/Sign/Install/Load/Kernel/GPU Runtime | NOT RUN |

Native源码allowlist排除device/plugin/PCI/MMIO/PSP/ring/真实VM硬件实现。
C++17、无异常/RTTI、freestanding、mkernel/fapple-kext/nostdinc++、Core4KiB栈限制，
x86无red-zone。输入对象minos26.5/sdk26.5；最终Kext类型文件保留13个内核导入，
无LC_BUILD_VERSION，文件构造不等于内核解析成功。不存在可安装Bundle、设备匹配或部署流程。

19类负样本实际被拒绝：M12的10类加9类SDK/部署目标/参考来源/hash/格式/真实API
类型错误/非法初始化路径。旧15参考、SDK27头/对象都不能混入正常26.5构建。
puts负Kext仍让ld返回0，独立政策拒绝，因此没有用linker exit0代替KPI闭合。

## D. Navi44实际代码

1. core/driver_model.hpp/.cpp：通过既有N44Q codec规范化候选，拒绝Navi48及能力注入；
   复用显示timing/assess，拒绝未知connector、编码和链路不匹配。所有硬件权限false。
2. core/displayid.hpp/.cpp：单EDID DisplayID扩展的版本、双checksum、边界、padding、
   primaryUse和块目录。continuation拒绝；仅opaque容器，不解码详细时序，不自动进入
   既有EDID模式集合。固定MIT Linux参考、license/归属保留，没有编译Linux代码。
3. platform/resource_model.hpp/.cpp：8条目CPU地址/预算/重叠/对齐账本，复用AccessOps/
   GenerationClock，实例/generation/serial隔离。Pending/TimedOut阻止提前释放；
   Stop/Reset只撤销，必须显式CPU取消确认后才归还。没有VRAM、真实GPU VA或提交。
4. platform/lifecycle.cpp：修复ScopedInput::length在权限/别名检查前改写输入的缺陷。
   保留旧调用方的普通输出清零语义，输入别名失败时不改数据。
5. m13_target.py/run_m13_checks.py/m13_abi_reference.py：显式SDK profile、Header来源/
   版本审计、对象标签/参考hash/类型负样本、完整编译provenance及SDK26 ABI整理。
   原run_m11/run_m12/run_host_tests文件未修改，只在已审核包装副本内重定向输出和目标。

原ASIC、Discovery、Firmware/ELF、EDID/CTA/AtomBIOS、N44I/N44Q、NativeOwner及
Shutdown继续保留。真实Navi44拓扑/firmware/connector/DCN/DMUB、VRAM/VM/IRQ/queue
仍缺硬件依据。Navi48/gfx1201参数不能直接套用gfx1200。
合成1440p180时序与预算通过不代表训练、scanout、DP/HDMI或Metal成功。
功能矩阵与依赖图见docs/m13/navi44-driver-architecture.md。

真实Publisher引用、callback取消来源、内核waiter drain及最后free仍未完成运行验证。
Native Gate/Owner已重编译，不宣称Host mutex等于内核线程安全。

## E. 测试

M12旧基线先实际复现；随后在SDK26.5上重跑原C++161+74+59+34，Python91PASS/2SKIP，
744共享差分、2400解析变异差异0，2400 EDID/ROM及800 Query有界输入通过。
历史失败注入和并发覆盖继续保留，均不计M13新增。
M13新增54项行为检查、500组固定种子759013的DisplayID容器变异。
普通、ASan+UBSan、TSan实际通过；重复模式不累计新增数量。策略负样本为19类，
其中原10类属于回归，新9类单独可追踪。Core14/Native5静态分析无警告。
ASan leak detection未验证；TSan只覆盖Host路径，Kernel Runtime仍NOT RUN。

ScopedInput长度别名问题用实际M12提交源码独立编译复现，新断言失败、exit1；
修复版54/0。早期legacy包装器因文本替换出现两处同字符串而在编译前终止，
改为锚定首行后通过，原始失败说明保留。XNU/Linux源路径404未假装取得，
更正LinuxDisplayID路径后确认MIT文本；未确认的声明在记录中仍UNVERIFIED。

Windows、x86用户态运行、CMake配置/执行、真实内核、GPU/显示/Metal均NOT RUN。
CMake增加显式SDK26.5校验及M13 CPU目标，但本机没有现有CMake，不安装。

## F. GitHub

远程只读复核main仍6b088ba，Public分支sync/m9-m11-sanitized仍fd9b9032。
独立忽略的发布Repo从已审核fd9b9032继续准备sync/m9-m13-sanitized，精确导出
M12/M13最新源码及可公开摘要，不继承原私人提交祖先。
公开副本替换路径标签，排除raw日志/SDK/二进制/固件/原始Git；不篡改测试结果。
具体候选SHA、完整文件/新增可达对象审查、发布树独立Host/Sanitizer结果及差异见
publication-audit.json。发布树Native构建若未运行就保持NOT RUN，不借开发树PASS。
**未获本轮推送确认，NOT PUSHED，main不变**；M12/M13原开发分支不得直接推送。

## G. 安全

所有任务主动源码/产物/TMP/cache/日志/Git准备写入在Lab。检查真实路径/所有者/
symlink/hardlink，父Git和M6–M12原始报告/补丁/旧许可证保持；新MIT归属追加保留。
实际workspace-write范围更广，路径检查不等于绝对OS隔离或TOCTOU证明。
没有sudo/权限扩大、系统/EFI/NVRAM/SIP/APFS/KC/显示配置修改；未运行部署、
GPU/Windows/第二SSD或未经审核第三方脚本。无新SDK/KDK/工具安装、无GitHub写入。
在线只读官方资料和少量固定源码，不把公开文本用作混合SDK。

## H. M14

目标ABI比M12更接近：真实26.5声明/对象与26.5源码参考现已匹配。
下一步须固定真实系统build，取得经独立批准的合法对应KDK/二进制，核验KPI、
vtable和实际内核ABI；SDK25F70本身不证明目标内核。
可继续纯CPU：publisher/锁等待者生命周期、scope消费者、依据公开格式的时序解析、
BO/VM/fence/reset模型和wire协议。真实Navi44显示必须补足实卡数据、DCN/DMUB/PHY/
固件/时钟与OS图形栈。唯一显卡/无核显的黑屏风险尚不可接受。
本轮结束后停止，不自动进入M14、Kext运行或硬件实验。
