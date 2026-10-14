# M10 开发报告：Darwin 部分链接与生命周期

2026-10-14，Asia/Shanghai。真实Apple Silicon Mac，macOS27.0.1/26A434，
Apple Clang21.0.0/clang-2100.3.34.2，Xcode27/macOS27 SDK，既有Python3.14.5。
源码开发、CPU测试、真实内核头文件编译和非部署型部分链接均已实际执行。
原始日志保留本地，公开JSON中的PROJECT_ROOT/PYTHON标签是隐私替换，不是原始argv。

## A. Git 与接管

真实项目仍为用户指定的Lab，repo root与cwd完全相同；所有权/路径/链接检查通过。
M9原始提交`498e97fd3e92fbb243e303fcc381a4a6e6bef07b`已存在，接管时clean。
origin与用户指定唯一URL相同。M9交付manifest逐项匹配，没有重复创建M9研发提交。
M10从此提交创建`m10/darwin-link-lifecycle`，没有从旧main开始。
父目录独立Git仅只读保存元数据哈希，未修改其index/config/refs/history。

远程只读观察：只有main，SHA`6b088ba47a1b9f1bc2493cc03e12e2dae94d1d18`，
M9分支未存在。M9有9个文件包含私人绝对路径，原提交不能直接满足本轮发布隐私条件。
已准备19文件脱敏发布树`5cb3cab30f59e817d48b9bcc5d579e1e05f4638f`，
清单见m9-sync-review.md；需要独立正常快照提交避免上传原私人路径祖先。
原M9报告/日志/补丁不改写，公开版本标记编辑性路径替换并保留事实。
用户尚未确认该发布步骤，未创建发布commit或推送。M10不依赖该推送。
本轮本地M10提交SHA另存ignored local/local-commit.json，不嵌入自身SHA。

## B. 实际源码改进

- platform/contract.hpp：Lease在外部release之前失效指针/长度，回调期间拒绝open/close重入；
  增加地址范围检查。NodePool精确核对归还指针/数量，并清空Node；错归还不解锁。
- platform/lifecycle.hpp/.cpp：基于原契约实现SnapshotOwner、ReferenceOps、8个ticket预算、
  immutable View、上下文检查、generation/serial/slot、撤销/关闭屏障、prepare/complete清理。
- platform/darwin_snapshot.hpp/.cpp：真实OSData/IOBufferMemoryDescriptor私有CPU副本，
  显式工厂引用1→owner retain→释放工厂引用。长度/地址/公开raw OSPtr ABI断言通过。
- host/lifecycle_mock.hpp：真实用户态mutex/TLS gate、逻辑引用和受控失败注入。
  没有将Mock称为IOKit对象或内核锁。
- tests/unit/m10_lifecycle.cpp：74项生命周期行为，600组有限失败注入、240次并发访问。
  m10_regression_proof.cpp真实对照旧/新头，m10_host_dependency.cpp真实Host导入负样本，
  m10_contract_compile.cpp真实Kernel契约布局/类型探针。
- run_m10_checks.py：显式host/native/partial-link/all目标，分离原始/公开日志，严格
  源码allowlist、真实工具、对象/符号/架构/重定位/部分链接/静态分析，串行有超时。
- CMake：新增纯CPU生命周期与回归证明目标，保留原源码、异常/RTTI禁用和串行timeout。
  CMake本机未运行/未安装；没有加入Native、硬件、fetch/install或部署目标。

Windows和旧Core逻辑没有删除；本轮没有Windows环境，Windows Regression=NOT RUN。
device/plugin/profile/Makefile、N44I/N44Q、原解析/能力门禁不变。

## C. 内核对象与符号

每架构14个真正内核头编译对象；架构分别x86_64/arm64，均MH_OBJECT。
实际nm undefined/defined及提供方形成symbol-audit.json；每架构20个INTERNAL_RESOLVED。
全量组合后x86剩7个EXPECTED_KERNEL_IMPORT，arm64剩6个；UNKNOWN=0、
HOST_ONLY/UNSUPPORTED正常集=0。实际Host `_puts`对象被负样本策略拒绝。
真实对象用错误CPU调用审查器也被拒绝。不是仅凭源文件名判定。

剩余：IOMallocAligned、IOFreeAligned、IOLog、memcpy、OSData::withBytes、
IOBufferMemoryDescriptor::withBytes；x86额外__bzero。完整mangled拼写见JSON。
公开XNU固定`f6217f891ac0bb64f3d375211650a4c1ff8ca1ea`的公共及对应架构导出表
有实际条目，文件SHA及别名见export-reference.json。没有伪造实现或导出。
参考导出存在不证明目标内核二进制导出、vtable、ABI或最终链接匹配。
所有外部条目仍REQUIRES_REAL_KERNEL_LINK。

内核ABI审查覆盖同一真实SDK/编译选项、无异常/RTTI/Host heap/stdio/pthread/stack-check泄漏、
布局/宽度断言、Mach-O架构/platform/load commands、DWARF verify及重定位审查。
arm64通用对象不是arm64e/PAC认证；OSObject真实二进制调用未执行。

## D. Partial Link

真实已有Apple ld-27037.1；对两架构执行`ld -r -arch ... -platform_version macos 13.0 27.0`。
两个partial产物均PASS、单架构MH_OBJECT，无运行入口/dylib加载/全局初始化。
内部依赖实际消失，外部KPI仍保留；源文件、对象SHA、load commands、relocations全部记录。
原12个M9对象也已在本轮实际部分链接，剩5个外部导入，原对象SHA逐一匹配。

没有Kext Bundle/Info.plist/设备匹配、签名、安装、Kernel Collection操作或执行内核代码。
部分链接成功不是Full Kext Link成功；13.0部署标记也不是目标实机兼容性结果。

## E. 真正实现的生命周期规则

只在可信caller提供的gate由普通线程持有时操作；回调递归拒绝。
CREATED→ACTIVE→CLOSING/REVOKED→RELEASED，初始化或complete失败到FAILED。
owner持有1个额外强引用保护全部tickets。borrow/read在revoke/close后拒绝并清空输出；
已存在ticket仍须归还，最后归还才complete→release。重复close、归还及外来token不会多释放。
占用中的ticket不会被新borrow覆盖，错误归还不会丢失其他owner的有效归还义务。

prepare失败不complete；complete失败不release，保留prepared/引用，允许清理重试。
初始化失败清空视图并配对release；两个资源部分创建失败做了逆序清理验证。
creator先drop引用时，owner引用保证最后borrower之前资源仍在；Model真实CPU计数已验证。
NodePool返回校验、内存对齐/地址溢出、容量不足、非法上下文和shutdown pending均有断言。

Native实际调用仍仅编译。OSData/Buffer retain/release、prepare/complete内核执行NOT RUN。
Native副本代码不调用prepare/complete、DMA/物理地址/映射接口。
真实IOService stop/free、owner存储强引用、generation发行器、内核gate和实际撤销仍未实现/验证。
存储必须长于tickets；readyToFree是caller必须落实的屏障，不能合法调用已销毁的C++对象。
generation须唯一，ticket不是用户权限认证；缓存裸View不能被逻辑撤销自动取消访问。

## F. 真实测试与失败记录

| 类别 | 本轮结果，重复不累计 |
|---|---|
| 原arm64 C++ | 34+31+96=161 PASS，0 FAIL |
| 原Python | 91 PASS/2 SKIP，含4个静态安全断言 |
| 新生命周期 | 74 PASS/0 FAIL；普通、ASan/UBSan及TSan重复不计新增 |
| 初始化失败注入 | 600组，固定规模，invariants PASS |
| 并发Mock | 240次worker访问+一个shutdown待归还borrower，错误0、complete/release各1 |
| 共享差分 | 744输入，0差异；原基线对象和M10对象分别验证 |
| 解析变异 | 2400输入，seed759070，0差异 |
| 显示/Query | 2400+800输入，原invariants保留PASS |
| ASan/UBSan | arm64原161及新74、有限差分/变异PASS；leak NOT VERIFIED |
| TSan | 实际编译链接运行PASS；生命周期/Host gate插桩，旧非并发parser未插桩 |
| Static Analyzer | 11个CPU/contract单元零warning；另2个真实Kernel Native单元零warning |
| x86 Host | 编译/链接PASS，运行NOT RUN；不安装/触发Rosetta |
| 两架构Native/partial | 14对象各自编译/分析/组合PASS |
| Full Kext / Kernel / GPU / Metal / Windows | NOT RUN |

真实Core不允许实际shader/Discovery capture的两项Python SKIP继续保留。
M9基线先运行原portable测试并重定向M10输出；共享差分随后链接保留的编前M9纯对象复现。
原12 Native对象未冒称本轮重新编译，而是hash核对后复用；M10真实新编译14个/架构。

旧/新行为证明真实发生：M9头的程序exit1，LEASE_RELEASES=2、错误Node归还后locked=0；
修复后同程序exit0，releases=1、locked=1。该预计失败不是当前功能测试失败。
测试回调/condition-variable等待有边界，不让坏实现递归无限运行。

实际普通源码错误：第一次新Native假设OSPtr是智能指针，`.get()`导致真实Apple编译4处错误。
阅读实际OSPtr.h后使用公开raw ABI并明确释放工厂引用，保留首次错误再重跑通过。
初次符号UNKNOWN为遗漏对应架构导出表，依据真实固定源补齐，没有改名/删API/伪造定义。
补充M9基线probe首次漏`-I`导致ipdiscovery.hpp找不到，补显式include后真实差分通过。
另有一次Git ls-files未用-z造成中文文件名被quote，改用-z，未删除/覆盖任何文件。

每child60秒、测试/差分30秒、外层host600秒且child独立超时。串行/有限线程/输入，
没有无界fuzz或GPU benchmark。普通输出和真实exit保存local；公开argv做路径标签替换。

## G. 安全与历史

实际workspace-write沙箱执行，所有显式写入在授权Lab及合法子目录，TMP/cache也在Lab。
链接和Kernel编译没有扩大权限。M9发布请求待人类确认，未因时间经过视为批准。
未sudo、系统/全局配置、EFI/NVRAM/SIP/启动安全/磁盘/APFS/快照操作；
未安装任何组件、Kext/SDK/工具，未签名/加载，未连接Windows，未执行GPU/MMIO/DMA/固件。
未运行上游Makefile/安装器，未Actions/外部CI/PR/Force Push/main修改。
Apple SDK头未复制/上传；导出表原文仅本地参考，非SDK安装。
历史M6–M9报告、补丁、许可及父Git字节核对见integrity-audit.json。
有日志/产物的目录ignored，精确stage，不使用git add .或危险清理。

实际沙箱允许范围比Lab子目录更广；不宣称子目录是系统唯一可写路径。
路径检查不等于并发TOCTOU防护；正常OS/工具自动缓存不构成物理零副作用证明。
没有独立全盘系统审计，秘密模式扫描也不是任意秘密不存在的证明。

## H. 成熟度

| 阶段 | 证据边界 |
|---|---|
| Windows离线软件 | 历史验证保留；本轮Regression NOT RUN |
| macOS CPU软件 | 实际PASS，Core/Mock/Sanitizer/有限并发 |
| Darwin Object | 两架构真实头编译PASS |
| Kernel Partial Link | 两个Relocatable Object PASS，KPI未最终解析 |
| 可链接Kext | Full Kext Link NOT RUN |
| 可加载Kext | 签名/加载/Kernel Runtime NOT RUN |
| 真Navi44显示 | NOT RUN |
| Vulkan/Metal | NOT RUN |

## I. M11建议与停止

可继续准备独立授权的非部署Full Kext工程验证。先固定目标macOS/XNU/合法完整链接资料，
核对KPI/类ABI，设计没有硬件匹配路径的服务/入口骨架，以及真实owner存储/引用/gate/
stop-drain-free与唯一generation。见m10-build-readiness.md与remaining-blockers.md。
目前不能保证Full Kext链接或真实资源恢复；对象PASS与参考导出不代替目标内核证据。
不在本阶段尝试Bundle、签名、安装、加载或GPU。用户确认M9同步/M11范围后再行动。

交付包括源码、6份设计文档、基线/编译/Native/符号/partial/test/分析JSON、原始本地日志、
`patches/m10-from-m9.patch`及本地Commit。公开文本最小化私人路径，原始记录不篡改。
本阶段交付后停止。
