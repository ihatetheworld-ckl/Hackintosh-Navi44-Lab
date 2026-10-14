# M8 完整开发报告：Navi 44 显示核心与Darwin就绪工程

日期：2026-10-14，Asia/Shanghai。项目：Hackintosh-Navi44-Lab。
环境：Windows11，现有LLVM-MinGW；范围：实际源码、CPU-only编译、静态字节测试。

## 1. 核心结论

本轮在M7项目上实际增强EDID/AtomBIOS，形成可复用显示数据模型；
完善typed scratch/input lifecycle/serialized contract，新增CRC工具、ELF预算和N44Q候选协议。
源码已在Windows以禁异常/RTTI、freestanding及严格警告编译，完成离线回归、差分、Sanitizer。
它们是未来驱动的基础纯逻辑模块，没有接入真正RX9060XT。

Darwin native、macOS/kext、GOP/framebuffer输出、DP/HDMI训练、GPU firmware/VM/queues、
Vulkan/Metal/WindowServer、1440p180实测、双盘安装全部NOT RUN。
没有因为测试PASS把模拟能力提升成真实硬件支持。

## 2. 接管与M8基线

核对M7交付manifest、工具与关键源码，保存reports/m8/history和baseline-sha256。
M7测试独立重定向到reports/m8/baseline与build/m8/baseline；历史report未覆盖。
独立基线重跑：Python89PASS/2SKIP、C++65PASS、743组差分、2400变异、3143 sanitizer输入、
两类故障canary。上述仅为M7基线复现，不计M8新增。
Git核对实际发生在交付审查阶段；开发前以M7哈希建立基线。
Lab根没有.git，使用快照/增量补丁追溯；两个upstream固定HEAD及只读status已记录。
所有既有report/patch历史hash再核对，见history-integrity.json。

## 3. 实际源码模块

| 模块 | 实际增量 |
|---|---|
| src/edid.cpp | DTD失败清空、geometry、CTA offset/DBC/vendor长度/容量/错误拒绝 |
| src/atombios.cpp/.hpp | image范围、版本、表重叠/循环/路径/records/失败状态、索引修正 |
| core/display.hpp/.cpp | Monitor/Mode/Connector/Link/Engine/Fit、解析转发、去重与64位数学 |
| platform/contract.hpp | ScratchOps/ExecutionOps、snapshot release、RAII清理、NodePool |
| host/platform_mock.hpp | 真Node数组、context/reentry/lifetime行为计数 |
| platform/darwin_native.cpp/.hpp | nativeScratchOps引用构造好的pool；仍仅静态源码 |
| core/integrity.hpp/.cpp | 显式CRC convention、checksumMatched与signature/loadable分离 |
| core/validation.cpp、host/navi44.py | ELF16MiB/4096 headers预算同步 |
| core/query_candidate.hpp/.cpp | N44Q1.0编码/解码、来源/epoch、OfflineOwner lease状态机 |
| tests/fixtures/m8_display.hpp | 合成EDID/CTA/ATOM，非本机数据 |
| tests/unit/m8_unit.cpp/m8_fuzz.cpp/m8_contract_compile.cpp | 固定预期、恶意输入、有界变异、kernel-friendly contract编译 |
| tests/test_m8.py | ELF输入/headers预算新Python测试 |
| run_m8_offline_tests.py/CMakeLists.txt | 独立流水线、显式source allowlist、串行/timeout |

没有复制一套新EDID/ROM原始解析器。保留原公共接口、DMT/VIC逻辑和许可头；
新Core包装提供统一严格Result。文字编辑可能统一行尾；补丁按字节重放验证。
真实改动清单见changed-files.json，补丁patches/m8-from-m7.patch。

## 4. EDID实际支持与限制

支持1.3/1.4、128B blocks/Header/Checksum、manufacturer/product/digital、
progressive数字separate-sync DTD、已有DMT/CTA-VIC子集、CTA rev3 DTD与HDMI TMDS/SCDC声明。
声明extension数与输入精确匹配，最多4块。非法timing、未知版本、跨界DBC、
容量不足与损坏内容拒绝，失败清空结果。
相同timing去重合并source；同尺寸同刷新而不同raster保留alternative。
默认未知extension拒绝；KnownBlocksOnly保留已知部分并标partial。
未解析timing计数，不假装完整支持。

未支持DisplayID、EDID2、interlace/stereo/边框/模拟复合同步、
完整HDR/FRL/DSC/VRR、所有VIC或CVT/GTF公式。
没有DDC/I2C/AUX/Windows GPU API读取。所用fixture全合成，未读取本机EDID。

## 5. AtomBIOS实际支持

55AA、512B块长度、镜像sum8，ATOM2.2/2.3已知前缀、master data2.1、
display object1.5、path_v3、静态I2C/HPD、connector类型。
每个访问限于当前image；外层ROM多余数据不能补足坏指针。
拒绝表重叠/self-cycle/重复connector、错误版本/reserved/count、
path数组内record偏移、0长度/无终止/重复record。
修正DCE27/VRAM28/Voltage32索引；v1.4不再混作v1.5。

只有版本化静态信息，无ATOM bytecode执行、PCIR完整多image验证、真实encoder/PHY routing。
特殊USB-C保留字段配置未支持。真实Navi44 ROM/connector地图仍UNVERIFIED；
其他板卡历史描述不是本机复现，也未新增使用未确定许可的ROM样本。

## 6. Display Capability如何防误判

EDID声明、connector静态description、link预算、engine预算分别建模。
Origin只是Unknown/Synthetic/StaticReference，不是可信硬件认证。
refresh使用64位约分的精确分数；geometry、clock、rate与buffer capacity设明确预算。
DP8b10b和TMDS RGB24/30/36bpp做理想payload预检，引擎clock独立判断，
unknown不升级，WithinBudget也不等于协议/链路已通过。
hardwareVerified、boardVerified、routingKnown与outputAllowed不被离线解析授予。
没有生成真实mode switch或DP/HDMI Adapter。

1440p180有效像素663552000/s，高于经典DTD最大655350000Hz；
必须进一步研究DisplayID/其他表达，本轮不支持本目标EDID模式。
合成2720×1500、734400kHz模型只证明算术180Hz：
32bpp frame14745600B，完整写入2654208000B/s，帧时间5.56ms。
这是数学，不是性能或输出结果。

## 7. Darwin Adapter增量

M7 raw byte scratch改为ScratchOps提供真正构造的Node，Host Mock改为Node[512]。
NodePool长期owner存储；native接口引用pool，避免未证明的raw-byte cast/对象生命周期。
Snapshot借用需成对release；ExecutionOps明确serialized thread前置条件。
异常上下文/重入/missing callback拒绝；parse失败/资源不足都配对归还input与scratch。
执行上下文拒绝时不调用日志，避免错误线程IOLog或递归logging。
tests验证这些真实CPU行为，没有假的IOKit类型。

真实OSData/descriptor retain、IOService start/stop/open、锁与task teardown还只读设计；
Mock bool不是kernel并发锁。native API/SDK与Mach-O未编译，
pool实际放置、线程gate、kernel总栈、符号/ABI和对象析构仍需macOS验证。
固定SDK IOService头和官方OSObject/IOLib已阅读，部分pin网页失败如实记录。

## 8. Firmware / ELF增量

CRC-32 ISO-HDLC：反射poly0xedb88320、init/final XOR0xffffffff，
对标准123456789及空/损坏payload做实际测试，未知convention拒绝。
checksumMatched与signatureVerified/loadable分离，后二者始终false。
公开AMD common header说明payload CRC字段，但所读Linux路径只核对总体大小，
不足以证明所有实际固件的CRC convention。没有盲目接入默认Firmware/PSP路径：
原非零CRC未验证拒绝仍保持，未知signature仍未验证。

ELF输入最多16MiB、phnum+shnum最多4096，Python/C++同步；
原symbol/descriptor/kernarg/relocation/metadata checks保留。
大输入不能穿过Host1MiB传输，改为每语言直接单元测试；未放宽Host门禁。
ALLOC relocations仍不支持，没有应用重定位/Shader执行。
真实gfx1200编译产物仍SKIP，未改Machine造假。

## 9. Cobalt生产ABI候选的实际成果

新增N44Q1.0/128B codec，内嵌N44I v2/96B，显式LE/version/length/provenance/presence/epoch。
未知minor、能力、verification、owner或reserved拒绝；来源标签不是认证。
OfflineOwner支持单CPU lease、close、monotonic generation与stale token失败终止，
永不允许GPU初始化。不是实际资源所有权或UserClient。

固定Cobalt native header实际minor12、QueryInfo192B，AMDRadeonRDNA4 header minor9；
旧patch2内嵌更早版本。审查角色/route权限及query预算，APP拒绝ReadRegs/scanout。
不混用headers，不将128B复制到192B，不把gfx1201 canned topology用于Navi44。
生产差距仍包括可信kernel采样、task权限、exclusive owner、BO/VM/fence、
映射撤销/reset、实际gfx1200代码与Mesa winsys；没有Vulkan或Metal新实机能力。

## 10. 工具链和真实构建

LLVM-MinGW20261006，Clang23.1.3，target x86_64-w64-windows-gnu。
旧ZIP SHA256：317492c456aa27ee607a5919f1d2d38dcdc1112516a24d0bf4b00d078f52d17a。
本轮重新核对实际compiler/nm/symbolizer/config/runtime与ZIP成员一致，未下载/安装。
9个Core translation unit真实使用：
C++17、-fno-exceptions、-fno-rtti、-ffreestanding、-Wall/-Wextra/-Werror、
-Wframe-larger-than=4096、-O1/-g；对象nm审查。Kernel contract另编译检查。
Host保留STL便利层；未链接device/plugin/IOKit/native。产物为WindowsPE/COFF。
仍需memcpy/memset及内部Core符号，不能宣称Apple ABI或完全freestanding。

统一真实入口：

~~~powershell
& 'D:\RuntimeEnvironment\mise\mise\data\installs\python\3.12.13\python.exe' -I -B -X utf8 run_m8_offline_tests.py
~~~

所有实际argv、exit、持续时间见commands.json；构建详情见build-results.json。
普通compile/link/unit/diff/fuzz/analyze exit0；canary非零为预期检测。
CMake修改后静态审查显式source与CTest timeout，现有Safety tests重新通过；
实际CMake configure/build、MSVC/native SDK均NOT RUN。

## 11. 自动化结果（最后一次执行）

| 分类 | 结果 |
|---|---|
| 原Python回归 | 89 PASS、2 SKIP；89中4项静态检查 |
| 新PythonM8 | 2 PASS |
| 原C++回归 | 65 PASS（34+31） |
| 新C++M8 | 96 PASS |
| 共享差分 | 743原corpus+1新预算=744组，零差异 |
| 原确定变异 | 2400组，seed759070，零差异 |
| 新EDID/ROM变异 | 2400组，seed759080，invariants PASS |
| 新query变异 | 800组，同一PRNG续序，invariants PASS |
| Sanitizer | 原3143 corpus/变异、新3200变异及M7/M8单元均通过当前覆盖 |
| 检测器canary | heap-buffer-overflow/整数溢出实际检测 |
| 静态分析 | 10文件零warning |
| Core flags / object symbols / contract | PASS |
| 真ROM/EDID、gfx1200ELF、Darwin/Kext/GPU | UNVERIFIED/NOT READ/SKIP/NOT RUN |

Python总91 PASS、2SKIP；C++总161 PASS。
不把基线额外复现、重复sanitizer执行、truncate循环输入和静态assert再计入新单元数量。
原差分与新fuzz不是同一种验收，不能拼出“GPU支持总PASS”。
新模块不强行重复写Python Parser，以固定规范值、C++行为与Sanitizer验证。

~~~text
M8_FUZZ seed=759080 inputs=2400 accepted=479 rejected=1921 invariants=PASS
M8_QUERY_FUZZ inputs=800 accepted=10 rejected=790 invariants=PASS
~~~

每进程30/40秒，串行、有限规模，输入immutable invariants、失败清空与能力零提升。
有界变异不是coverage-guided；未验证leak、真实并发、kernel/硬件稳定性。

## 12. 失败与修复记录

- 重定向baseline runner把import root放在reports/m8：ModuleNotFoundError。
  修正project import路径，保留baseline-first-failure.log/command。
- 首次新Core编译遇unused kAtomSignatureOffset：使signature检查继续使用真实常量；
  -Werror保持，没有屏蔽警告。
- 新大ELF差分：probe返回input_size，Python Core返回elf_input_budget。
  属于Host传输与Core层限制差异；保留差异文件，取消跨层不适用case，
  追加各语言直接budget断言，保留1MiB Host限制与所有原差分。
- timing再验证输入可别名out.timing：先复制输入再清空输出，加alias-safe测试。
  此为代码审查修复，不冒充Sanitizer发现。
- 交付审查发现ExecutionOps拒绝后仍log可能违反线程上下文且递归；
  拒绝路径不再调用callback，增加有界logging重入断言后重新回归。

其余测试PASS；失败日志/JSON/commands保留在regression/execution/attempts。
未关闭Sanitizer、删除原测试、放松格式校验或修改已有通过预期掩盖问题。

## 13. 安全审查

所有主动写入限Lab；沙箱范围更广，依靠逐命令人工审查、路径检查与allowlist补充，
不宣称Lab专属系统隔离或TOCTOU绝对防护。
未修改Windows系统/驱动/注册表/服务/全局PATH，
未动EFI/BCD/BIOS/Secure Boot/TPM/BitLocker、未操作分区或读取Intel第二盘内容。
未访问GPU BAR/MMIO/ROM/VBIOS/DMA、没有firmware/queue/指令或显示配置更改。
未安装/加载kext/SYS、未管理员提升、未远程Mac/CI操作或Git推送/PR。
正常OS/工具可能产生缓存/日志，未做独立系统级审计，不承诺绝对零副作用。
原device/plugin/profile/Makefile gate保持，实际编译source allowlist排除硬件backend。

## 14. M9建议：优先真正macOS编译

| 类型 | 后续任务 | 所需授权/主要风险 |
|---|---|---|
| A Windows CPU-only | DisplayID、合法静态样本、其他ATOM版本、CRC格式依据、ABIbudget进一步覆盖 | 后续独立Lab开发授权；仍无硬件，无无限fuzz |
| B 真macOS纯编译 | Core/Native真实头与Mach-O、符号/构造/retain/thread、CPUfixtures | 用户提供合法Mac与工作区并单独授权；不等于允许签名/加载/改安全策略 |
| C 真GPU实验 | 本卡Discovery/GOP/connector、DCN/DMUB/链路、电源/VRAM、输出恢复 | 必须单独硬件授权；唯一GPU且无核显，黑屏/卡死风险高 |

优先B：Windows已覆盖足够基础纯逻辑，继续堆积未验证寄存器代码收益低。
M9先用真实macOS编译Core/adapter object和运行CPU tests，仍不构建可部署kext或加载。
针对1440p180，A中的DisplayID是明确格式缺口，可有限并行安排，但不能替代B。
本轮没有自动连接Mac、安装SDK或执行任何下一阶段。

## 15. 来源与证据

E1官方规范/API；E2公开源码；E3本轮CPU运行证据（仅其覆盖范围）；E4作者自述；E5设计推断。
没有本机macOS/GPU E3。资料阅读日期2026-10-14。

- [VESA E-EDID A2](https://glenwing.github.io/docs/VESA-EEDID-A2.pdf)，2006规范镜像，DTD/扩展字段，E1。
- [Linux v6.15 DRM EDID](https://github.com/torvalds/linux/blob/v6.15/drivers/gpu/drm/drm_edid.c)，固定tag，CTA/DTD安全参考，E2。
- [AMD atomfirmware.h](https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/amd/include/atomfirmware.h)，AMD许可接口，移动参考，E2。
- [amdgpu_ucode.c](https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/amd/amdgpu/amdgpu_ucode.c)，字段/size检查，移动参考，E2。
- [RFC1662 C.3](https://www.rfc-editor.org/rfc/rfc1662.html#appendix-C.3)，1994，CRC算法参考，E1；不证明AMD固件CRC适用。
- [XNU OSObject](https://github.com/apple-oss-distributions/xnu/blob/main/libkern/libkern/c++/OSObject.h)，生命周期/并发限制，E1/E2。
- [XNU IOLib](https://github.com/apple-oss-distributions/xnu/blob/main/iokit/IOKit/IOLib.h)，allocator上下文，E1/E2。
- [MacKernelSDK IOService固定头](https://github.com/acidanthera/MacKernelSDK/blob/05094e5e88cec7caedbfb35e8449ed0db94bf95b/Headers/IOKit/IOService.h)，E2。
- [AMDRadeonRDNA4固定源码](https://github.com/RX4Darwin/AMDRadeonRDNA4.kext/tree/49f7f20c00dd154384418078f8a09e79c400a06a)，本地只读E2，BSD3原许可保留。
- [Cobalt固定源码](https://github.com/Almosst-DEV/Cobalt64/tree/d6c9aedf8e6526a39e349b5886cbc8c7ddf77f65)，本地native ABI/权限代码E2，许可按文件。

pin IOLib/IOPCIDevice网页抓取失败，没有编造阅读或SDK构建结果。
未下载第三方ROM/固件样本，未运行上游脚本。
新代码沿Lab BSD3许可；未移植Linux GPL实现，按格式重新实现和对照既有BSD解析器。

## 16. 交付与终止

完整报告development-report.md；baseline/test/build-results.json；commands.json；
changed-files.json；safety-audit.md；remaining-blockers.md；
history-integrity/git-status/toolchain-integrity/delivery-verification.json；
deliverable-sha256.json；增量patches/m8-from-m7.patch；六份docs和实际源码/tests。
补丁仅代码/文档，不包含GPU固件、可加载模块、安装器或构建exe。
补丁在Lab内新副本检查/重放并逐文件hash验证；原source/历史不通过重放修改。

M8授权范围内工程交付完成。所有实际硬件和macOS部署仍未执行。
本轮交付后停止，等待下一阶段独立授权。
