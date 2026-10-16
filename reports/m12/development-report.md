# M12 开发交付

本阶段完成真实源码改进、Apple编译、对象及独立策略审计、生命周期回归和已批准的
M9–M11安全发布。状态为 **COMPLETE_WITH_BLOCKERS**：SDK27对象/文件验证通过，
目标macOS15内核ABI及完整目标链接闭合仍受真实材料缺失阻碍。没有Kext/GPU运行。

## A. GitHub 安全同步

Public仓库ihatetheworld-ckl/Hackintosh-Navi44-Lab，ID1418325342。
独立忽略的发布Repo中，干净历史为公开main `6b088ba47a1b9f1bc2493cc03e12e2dae94d1d18`
→脱敏M9/M10 `072a7f78cef07364293b5dd06c1b115dfa70d1f1`
→M11 `fd9b90328f7f94d224995cc7fe70f3cb2605e577`。
103个变更文件、130个新增可达对象、576个完整可达对象审查，无敏感发现；原始M9
498e97fd、M10 bea45e35、M11 7af27ea9均不在发布祖先或其对象库。
发布版原C++161、M10生命周期74、M11生命周期59、Python91/2SKIP、共享差分744、
解析变异2400、显示/Query3200、ASan/UBSan/TSan实际PASS；Native发布树QA为NOT RUN。
精确清单及独立发布测试见publication-audit.json，未经测试的范围没有借用开发树结论。

用户明确“批准仅推送此审核分支”后，实际推送成功并通过GitHub API核验SHA。
main未变，未推送M12或原私人分支，不合并/force/创建CI。默认沙箱网络和首次凭据
查询各失败128，随后授权网络命令配合仅get的现有凭据成功0；没有打印/保存Token。
发布树C++和M11 runner与M11原始源码一致；旧M10 public Host profile及QA忽略规则
为已审核差异。原始本地日志/报告不变，公开副本使用替换标签，不改变结果/退出码。

## B. 目标与SDK

M12从M11最终本地提交`7af27ea9cffc03005964016aaf67f748a9efc84a`创建
`m12/target-xnu-abi`。接管manifest/source哈希核验通过，适用M11基线在修改前实际复现。
macOS27.0.1/26A434，arm64，Xcode27.0/27A266a、Apple Clang21.0.0/
clang-2100.3.34.2、ld-27037.1、SDK27.0、现有Python3.14.5。
全部当前编译命令、源/头哈希和产物SHA可追踪；raw命令留local，公开版保留替换标签。

Intel静态目标继续固定macOS15.0/XNU11215.1.10；Apple macos-150分发树xnu gitlink
实际核对为`8d741a5de7ff4191bf97d57b9f54c2f6d4a15585`。
官方Xcode16对应SDK15；本机只有26.5/27.0 SDK，没有合法匹配SDK15或目标内核/KDK。
公开源码/声明/导出表只证明A/B/C层，真实二进制D未验证，加载E未运行。
下载选项、许可、未实测预算及未取得SHA见docs/m12/macos15-sdk-gap.md；未擅自获取。

## C. Kernel ABI

各架构19个允许源码对象均在真实Kernel.framework下编译。内部依赖全部解析。
x86_64剩余导入：

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

arm64没有___bzero，共12个。全部属于curated目标导入且存在对应架构固定XNU导出
参考；正常对象未知/不支持/Host/EH/RTTI导入为0。每个实际拼写、demangle、调用源、
类型/宽度、KPI参考文件/hash、版本/运行风险见kpi-details.json及symbol-audit.json。
IOMallocAligned在参考中别名到IOMallocAligned_external，未自行提供实现。

实际SDK27布局：OSObject16、IORegistryEntry40、IOService136字节、align8；
当前qualified IOService init/stop/will/did的ZTV偏移为600/1496/1040/1048。
固定15头与27词法声明比对不替代预处理后的类布局：IOService/RegistryEntry/OSObject
序列相同，所有文件字节不同，OSMetaClass有override标记等变化。目标槽位未知，
未硬编码偏移或混合版本头。详细事实在abi-audit.json及docs/m12/ioservice-abi.md。

## D. 链接与独立拒绝

Object Compile、双架构Apple ld-r、实际文件格式/架构/平台、Apple工具检查PASS。
x86_64 ld-kext返回0并生成独立MH_KEXT_BUNDLE，独立parser审查通过，但保留13个
KPI引用；没有目标KPI加载解析证据。Full Target Link Closure=BLOCKED。
所有二进制只在build/m12，不生成Bundle/Info.plist/签名/设备匹配/安装或加载步骤。
Kernel/GPU Runtime=NOT RUN，Kext Loadable=UNVERIFIED。

10类负样本实际REJECTED：Host puts、unknown、EH、RTTI、未允许Kernel printf、
initializer、项目符号提供方错误、实际对象string/reloc索引变异、arm对象误作x86。
含puts的隔离负Kext仍被linker接受exit0，独立政策拒绝，因此exit0不单独作为PASS。
没有Apple Stub。符号及重定位范围、load command白名单、编译选项、强符号提供方、
initializer/TLS等独立核验补充Apple nm/otool/lipo/dwarfdump，仍不是完整加载器证明。

## E. 实际代码改进

- lifecycle.hpp/.cpp：不可复制/移动、无raw View getter的ScopedInput；有界copy/byte、
  withInput及自动borrow/return的consume。callback错误也归还，禁止回调递归/close/
  revoke及读写重叠；修复byte检查前清零导致的输入别名改写。
- shutdown.hpp/.cpp：Initialized与Active分离、初始化失败、scope访问受Barrier状态
  和operation gate约束；保留旧跨平台Created-start路径。
- darwin_owner_storage.hpp：显式start、stop/poll/consume；不公开lifetime/raw Ticket。
  初始化仍使用原NativeSnapshot真实factory/retain/release契约，不制造GPU Buffer。
- darwin_gate.hpp/.cpp：借用真实IORecursiveLock，ordinary/current-thread检查，
  拒绝interrupt/disabled-interrupt/reentry；锁由publisher拥有，未执行或分配内核锁。
- M12 C++探针：真实锁类型static_assert、gate RAII与Owner的scope/stop编译整合；
  独立IOService布局对象排除链接；真实负样本全部隔离。
- run_m12_checks.py、m12_macho_audit.py、m12_abi_reference.py：显式受限构建、
  独立对象/策略/负样本、匹配编译头哈希和源码参考比较，无自动下载/部署目标。
- CMake增加CPU M12生命周期目标及30s超时；本机CMake未安装，CMake运行NOT RUN。

物理Owner/lock存储必须长于所有Ticket/scratch/waiter。未来真实IOService publisher
须移除回调源、drain并持引用至最终free；当前编译探针不宣称生产服务已完成。
ScopedInput不能阻止恶意保存C++引用；旧兼容裸View未删除，逻辑撤销不改变缓存指针。
Runtime锁和OSObject引用行为未执行，Host mutex不等于内核锁。

## F. 真实测试与修复

历史基线在M12重跑：原C++161、M10生命周期74、M11生命周期59；Python91PASS/
2SKIP，744共享差分和2400解析变异差异0，EDID/ROM2400及Query800有界输入通过。
M10 600/M11 400失败注入、240/320并发尝试保留原覆盖，不能记作M12新增。
新M12 **34行为检查**、**300错误callback清理**、活跃scope期间发起Stop及
**160次关闭后并发尝试**通过。普通/ASan+UBSan/TSan各实际执行，重复次数不累计
成新测试数量；唯一C++检查为294历史+34新增。策略负样本10类单独报告。
Apple Static Analyzer当前Core11单元、Native5单元无警告。ASan leak detection
未验证，TSan只证明覆盖的Host路径；内核同步未验证。

失败证据：首次runner把4KiB内核stack flag用于Host main产生5248字节编译错误，
改为Core单独受限编译；后续load command白名单漏ARM优化hint，经真实otool确认
并加入有界数据检查。两次失败日志保留。byte别名缺陷还用实际旧实现独立编译运行
复现：exit1且新增断言FAIL，修复版34/0在全部模式PASS。没有修改断言降低门禁。
发布QA helper首次重定向顺序失败也留原始记录，修复后发布树独立完整Host回归通过。

Windows、x86 Runtime、CMake、Kernel Runtime、GPU Runtime全部NOT RUN。

## G. 安全与追踪

所有主动文件写入在Lab，编译TMP/cache显式设置，源码/头/产物有hash，历史报告和
父Git未变。实际sandbox比Lab可写范围广，路径检查不等于绝对OS隔离或全机审计。
没有sudo/系统/EFI/NVRAM/SIP/APFS/KC/显示设置修改、Kext部署、GPU/Windows访问、
新SDK或工具安装。只读公开资料与独立批准的精确Git推送是本轮网络操作。
发布资料与安全核验见publication-audit.json、safety-audit.md、integrity-review.json。
本地M12 Commit由交付记录读取；避免在自身commit内容里写循环依赖的SHA。
最终代码/报告以同一提交固定，源码patch及changed-files.json与执行hash核对。

## H. 成熟度

| 层级 | 当前结论 |
|---|---|
| Windows离线软件 | 保留历史成果；本轮Regression NOT RUN |
| macOS CPU软件 | arm64实际编译/链接/运行PASS；x86编译/链接PASS、运行NOT RUN |
| Darwin Kernel Object | 真实SDK27各19个PASS；SDK15 BLOCKED |
| Partial Link | 两架构PASS |
| Kext类型文件 | x86 MH_KEXT_BUNDLE Construction PASS |
| 目标ABI闭合 | BLOCKED；源导出参考PASS不替代目标二进制 |
| 可加载Kext | UNVERIFIED；Sign/Install/Load NOT RUN |
| Navi44基础显示 | NOT RUN |
| Vulkan/Metal | NOT RUN |

## I. M13条件

先独立授权合法匹配SDK15/KDK取得，再做准确x86目标导出和C++布局比对。
纯CPU还可完成publisher引用/取消/锁waiter drain、scope解析消费者、wire协议和
BO/VM/fence/reset纯模型。实际显示缺Navi44 Discovery/connector/DCN/DMUB/GOP/PHY/
时钟/firmware和OS图形接口，Navi48/gfx1201参考不能直接套用。
详细依赖图在docs/m12/navi44-driver-integration.md；任务结束后停止，不自动开始M13。
