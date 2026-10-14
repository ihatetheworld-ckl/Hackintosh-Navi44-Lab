# M11 实际开发报告

2026-10-14，真实Apple Silicon macOS27.0.1/26A434；Xcode27/27A266a、
Apple Clang21.0.0/clang-2100.3.34.2、Apple ld-27037.1、既有Python3.14.5。
已完成源码、CPU测试、真实内核头对象、部分链接和独立Kext类型文件构造。
**目标macOS15的SDK/vtable/KPI二进制兼容尚BLOCKED/UNVERIFIED**。
没有任何内核或GPU执行。原始日志local、公开argv路径标签有明确区分。

## A. GitHub与接管

M10基线`bea45e350509676915e2fffba1584b776f1adc5d`，M9祖先
`498e97fd3e92fbb243e303fcc381a4a6e6bef07b`，开始时clean，origin正确。
完整manifest按各自对应commit核验；源/历史/父Git哈希保存并重新比较。
M11从M10创建`m11/kext-link-engineering`，没有main实验或覆盖旧branch。
本地最终commit另存local/local-commit.json并在对话显示，不嵌入自身SHA。

Public远程main仍`6b088ba47a1b9f1bc2493cc03e12e2dae94d1d18`。
独立ignored发布repo正常init+仅公开main bundle；分支sync/m9-m10-sanitized，
commit `072a7f78cef07364293b5dd06c1b115dfa70d1f1`，直接父为该main。
65个变更文件，原私人M9/M10提交不在对象库/祖先，520可达/74新增对象实际模式审查无命中。
发布树实际CPU/Sanitizer测试完成，详情publication-review.md和publication-audit.json。
唯一源码差异为history-free Host profile，不运行缺失私人M9校准；Native发布QA NOT RUN。
未获推送确认，NOT PUSHED；本M11原始branch仍继承私人历史，不可直接推送。

## B. 实际源码改进

- lifecycle.hpp/.cpp：Ticket绑定live owner身份，防同generation/serial跨Owner误接受，
  占用输出不丢失归还义务。真实M10源校准CROSS_OWNER_READ_ALLOWED=1/exit1，
  修改后=0/exit0，见identity-calibration.json。
- shutdown.hpp/.cpp：复用SnapshotOwner，GenerationClock和最多八owner的Stop/Drain/
  Free屏障，先停止获取、逆序关闭、允许旧ticket归还、四轮失败清理预算、gate与重入检查。
- contract.hpp：NodePool idle查询，错误/未归还scratch仍阻止存储释放。
- darwin_owner_storage.hpp：private NativeSnapshot+barrier+NodePool长期存储，ACTIVE新
  scratch获取、关闭后归还、非idle不ready；真实Apple API仅编译。
- m11_lifecycle.cpp：59项新增行为、400组初始化失败、320次确定并发；m11_identity_
  calibration.cpp旧/新真实源对照。Native/kmod探针真实类型/原型和拒绝入口。
- run_m11_checks.py：显式目标、源码allowlist、超时/本地cache/日志、Mach-O/header/
  符号/类型/链接器负样本及静态分析。CMake新增纯CPU目标，实际CMake NOT RUN。

Windows实现/原Core算法不删除，原profile/device/plugin/Makefile安全门禁不修改。

## C. Intel参考目标

选择macOS15.0/x86_64、Apple公开分发tag macos-150、XNU11215.1.10，固定xnu
`8d741a5de7ff4191bf97d57b9f54c2f6d4a15585`；来源见docs/m11/target-macos-xnu.md。
这是静态历史参考，不是PC运行/安装认证。已安装SDK26.5/27.0，没有15 SDK；实际Native
使用27真实Kernel头。minos15只是选项；没有下载匹配SDK/完整内核链接依赖。

## D. Kernel ABI

每架构17个新编译MH_OBJECT，真实API函数指针/宽度/无EH/RTTI/Host-runtime策略通过，
真实SDK头依赖hash、CPU/platform/load commands/重定位/内部提供方记录完整。
x86部分/独立文件最终八个外部导入：IOMallocAligned、IOFreeAligned、IOLog、memcpy、
___bzero、OSData::withBytes、IOBufferMemoryDescriptor::withBytes、IOService vtable。
完整mangled拼写及固定公共/x86导出条目见symbol-audit.json。
x86 UNKNOWN=0；arm64七个外部项仅编译分类，未套用x86导出表。
IOService super调用实际使用当前SDK vtable偏移；15目标二进制/layout未验证。
原型或导出字符串相同不代替最终KPI/ABI闭合。

## E. 离线链接

| 项目 | 实际结果 |
|---|---|
| Object Compile | x86_64/arm64各17 PASS |
| Partial Link | 两架构Apple ld -r PASS，MH_OBJECT |
| KPI Audit | x86固定公开源导出分类PASS；目标二进制UNVERIFIED |
| Full Link Attempt | 实际Apple ld -kext，exit0 |
| Link Result | 独立x86 MH_KEXT_BUNDLE文件构造PASS |
| 目标完整链接/兼容 | UNVERIFIED/BLOCKED：匹配SDK/目标KPI输入缺失 |
| Bundle / Sign / Install / Load | 全部NOT RUN |
| Kernel / GPU Runtime | 全部NOT RUN |

文件留build/m11/checks/darwin-x86_64/n44-offline-linked.macho，不加入Git。
无LC_MAIN/dylib loads/全局构造器/EH；无LC_BUILD_VERSION，平台来自输入命令/对象。
真实KMOD宏元数据与拒绝start/stop，未创建可实例化服务或设备匹配。
SHA/大小/原命令/sections/导入/重定位在link-results.json及local。
`-undefined error`警告弃用，且真实_puts负样本也exit0；独立策略拒绝_puts，
没有用这次负样本或未定义符号宽容获得目标链接PASS，没有Apple API stub。

## F. 生命周期证据

Stop后无新Ticket/read；已有借用安全归还，最后借用后才complete→release；重复关闭
不双释放，错误index/owner/stale/copy保留有效义务。部分创建失败逆序清理。
complete失败保留prepared/ref、最多四轮错误重试；超预算保持FAILED，不静默free。
GenerationClock非零单调、占用/溢出拒绝；同地址reuse用持续issuer拒绝旧generation。
Ticket/指针不是认证；issuer不能有stale票时重建，逻辑撤销不能取消缓存裸View。
实际物理owner存储必须长于借用，readyToFree仅内部屏障，不许可任意调用OSObject::free。
真实Native API/内核锁/IOService引用与回调运行NOT RUN/UNVERIFIED。

## G. 实际测试、失败与修复

M10适用基线在M11目录重跑：旧C++161、Python91/2SKIP、生命周期74、两架构14对象/
partial、差分/变异/ASan/UBSan/TSan/CPU analyzer PASS，原M10输出不覆盖。

| M11最终覆盖，重复矩阵不累计 | 结果 |
|---|---|
| 原C++ + M10 + M11行为 | 161 + 74 + 59 PASS，0FAIL |
| Python | 91PASS/2SKIP，含原安全断言 |
| 新故障注入 | 400组，M10旧600另列回归 |
| 新并发 | 320次；stop时acquired2，其后denied318，errors0 |
| M10并发回归 | 240次worker + shutdown borrower，PASS |
| 共享/解析差分 | 744/2400输入，0差异，seed759070 |
| EDID/AtomBIOS/Query变异 | 2400 + 800，seed759080，invariants PASS |
| ASan/UBSan | 原Core及74/59行为通过；leak NOT VERIFIED |
| TSan | 74/59实际覆盖Host路径通过；Kernel并发UNVERIFIED |
| Static Analyzer | 11个纯CPU + 3个真实Native/probe，最终零warning |
| x86 Host | 编译/链接PASS，运行NOT RUN，未触发Rosetta |
| Windows/CMake | NOT RUN |

真实失败保留：M11基线重定向首次错改helper import导致ModuleNotFoundError，修正后通过，
原历史hash不变；初次Host断言误写Asic成员名，修正为现有函数；Native探针外置虚函数
产生大vtable/禁止依赖，改全部内联；外部probe任意free触发RetainCount警告，移除调用并
限制protected后真实零warning，没有屏蔽checker。原并发可能全拒绝，新增通知协议后
普通/ASan/TSan均明确stop时有两借用。编译/链接/运行/NOT RUN分别记录。

## H. 安全与成熟度

父Git及原报告/补丁/许可保持；系统/管理员/EFI/NVRAM/SIP/APFS/KC/驱动/硬件/Windows/
安装/签名/加载/新组件/Actions/推送未执行。只读公开Apple/GitHub资料，未取得新SDK。
显式产物路径在Lab。一次初始直接Clang没有定向TMPDIR，自动临时文件工作区边界
NOT VERIFIED；之后全部runner定向项目cache/tmp。安全报告坦承该限制及沙箱范围。

| 成熟度 | 证据 |
|---|---|
| Windows离线软件 | 历史保留，本轮NOT RUN |
| macOS CPU | 实际PASS |
| Darwin Object / Partial | 实际PASS |
| 非部署Kext类型静态文件 | 实际生成/检查PASS，KPI仍保留 |
| 目标可链接/可加载Kext | ABI闭合UNVERIFIED；安装/加载NOT RUN |
| 真Navi44显示 / Vulkan / Metal | NOT RUN |

## I. M12与交付

下一步先匹配合法15 SDK/目标二进制或选择另一个有对应完整资料的Intel版本，
校验vtable/导出，整合真实服务owner引用/gate/drain与错误隔离，继续纯CPU确定性测试。
新依赖获取须独立批准；硬件display/firmware/VRAM/IRQ/OS图形栈仍是未验证缺口，
GPU/Kext运行、PC系统/启动配置实验必须独立授权。当前文件构造不能解除这些门禁。

交付源码、六份设计、环境/基线/对象/ABI/符号/link/test/publication/安全JSON/报告、
精确变更清单、源码patch、原始本地日志及本地commit。完成后停止，不进入部署或GPU。
