# M7 完整开发报告：RX 9060 XT / Navi 44

报告日期：2026-10-14，Asia/Shanghai。项目：Hackintosh-Navi44-Lab。
范围：Windows CPU-only 实际源码开发、离线编译验证和未来 Darwin 静态准备。

## 1. 核心结论

M7 已完成现有项目接管和 M6.5 基线复现，在原解析实现上形成 Core / Host / Platform / Darwin 草案分层。
Core 的 metadata 树已替换 STL 容器/异常为调用方有界 scratch、借用 View 和 Result；
新增 PSP package 结构解析、ELF symbol/relocation 结构检查、N44I v2 编解码及 Host Mock。
原有安全门禁保持关闭，未开发或运行真实 GPU backend。

本轮完成的是跨平台底层纯逻辑工程化。Darwin native 已有可审查源码，但未构建；
Kext/GPU/显示/Vulkan/Metal/WindowServer/macOS 安装与双盘部署均 NOT RUN。
基础显示、完整加速和日常 macOS 的本机可用性没有被证实。

## 2. 接管、快照与基线

读取 README、CMake、旧 runner、development/src/host、tests、M6.5 报告和就绪文档。
修改前核对 M6.5 source/deliverable SHA-256，并保存 reports/m7/history 与 baseline-sha256.json。
基线只在 reports/m7/baseline 和 build/m7/baseline 复现，原 reports/m65 未覆盖。
M7 基线：旧 C++ 34 PASS、差分 537 零差异、种子759065 变异2400、
Sanitizer corpus2937及两类canary通过。它们属于基线回归，不算M7新增成果。

历史完整性结果见 history-integrity.json，Git只读状态见 git-status.json。
如目录没有 .git，status 非零表示无仓库，不能将此目录宣称为干净 Git checkout。
上游源码只读，未运行构建、脚本、submodule 或 hooks。

## 3. 实际源码与分层

| 文件/模块 | 实际改动及作用 |
|---|---|
| core/validation.hpp/.cpp | 无堆/无STL的 Result/View/Scratch、metadata、ELF、firmware、legacy ABI、PSP package |
| core/model.hpp | 现有离线状态机/firmware requirement 类型移入 Core，Host 别名保持兼容 |
| core/device_info.hpp/.cpp | N44I v2 96B数据编码/解码，presence与能力分离，未知能力拒绝 |
| host/validation_adapter.hpp | 旧 bool/error API 转发、Host 固定512节点 scratch |
| src/offlinevalidation.cpp/.hpp | 旧接口委托 Core；旧 State/Session 同一类型，不新增重复逻辑 |
| src/ipdiscovery.cpp | binary v2/table reserved字段校验；沿用原32/64位Parser |
| host/navi44.py | budget/package/ABI2/ELF符号重定位与Discovery语义同步 |
| platform/contract.hpp | CPU Snapshot / Memory / Log / Lease，显式所有权 |
| host/platform_mock.hpp | 固定CPU内存与失败注入，释放/日志行为可测试 |
| platform/darwin_contract.hpp | 可离线编译的通用Darwin契约，无Apple SDK伪造 |
| platform/darwin_native.cpp/.hpp | 真实Apple API静态草案，所有Windows构建排除，NOT RUN |
| tests/unit/m7_unit.cpp、tests/test_m7.py、m65_probe.cpp | 新行为测试和跨语言CPU数据protocol扩展 |
| run_m7_offline_tests.py / m7_safety.py / CMakeLists.txt | 新独立测试入口、路径检查和Core编译选项 |

完整改动列表与前后hash见 changed-files.json；增量源码/文档补丁见 patches/m7-from-m65.patch。
所有一次性转换脚本保留用于追溯，不是再次执行的研发入口。

## 4. Kernel-Friendly 规则与限制

固定宽度整数、显式长度View、减法式边界检查避免off+size溢出。
Scratch由调用方提供，Core不new/malloc；metadata节点、字符串只在解析期借用，不向外返回。
Package返回的payload View仍借用原输入，其寿命明确由调用方保证。
错误不是异常；失败清空scratch used和输出模型。未知版本/target/IP/能力均拒绝。

4个Core translation unit均实际以C++17、禁exceptions/RTTI、freestanding、严格警告、
4096字节单函数栈警告编译；对象符号检查未发现STL/new/unwind/throw/RTTI依赖。
仍有memcpy/memset与内部Core引用。没有完整总栈分析或Apple内核ABI保证。
Host兼容层大scratch与probe中的STL/exception保持Host-only，不能进入未来kext。

## 5. Discovery / Firmware

既有binary/IPDS版本、checksum、32/64位base、GC_INFO、多表、重复IP、范围与溢出拒绝保持。
M7新增reserved字段校验和Python同步；不是另一套Parser。
Firmware需求模型沿用GC/PSP/SMU/SDMA/DCN派生；失败清空全部条目，避免残留数据。
它是建议组件清单，不证明精确版本或真实Navi44固件可用。

新增PSP v2.0/v2.1 package读取真实公开header结构：
长度/descriptor范围、组件编号1..12、重复/overlap、SOS+SYS_DRV缺失检查。
v2.1非零aux和非零CRC仍拒绝；signatureVerified恒false。
Common v1.0仍保持严格规则，未知header/version/component拒绝。
CRC实现及PSP签名没有被宣称完成；本轮没有下载或上传真实固件。

## 6. ELF / Shader metadata

沿用ELF64 little-endian、EM_AMDGPU=224、gfx1200=0x48 / gfx1201=0x4e、段/section范围、
metadata版本、kernarg、kernel descriptor与group/private一致性验证。
M7新增符号表stride/link、REL/RELA stride/count/link/info及symbol index检查。
ALLOC relocation显式Unsupported，不应用重定位。不是通用GPU代码loader或shader ISA validator。
新增定向测试覆盖合法非ALLOC结构、错误symbol/stride/link及ALLOC拒绝。
真实gfx1200编译产物缺失，仍SKIP；没有人为改ELF Machine冒充编译成功。

## 7. Windows工具链及实际构建

现有LLVM-MinGW 20261006 / Clang 23.1.3，target x86_64-w64-windows-gnu；
LLVM commit 0d261d1ca552c95a8f007e061c787ac7132fbcbc。
既有ZIP SHA-256：
317492c456aa27ee607a5919f1d2d38dcdc1112516a24d0bf4b00d078f52d17a。
本轮重新核对归档及实际compiler/runtime与ZIP成员一致性；未下载或安装工具。

统一执行命令：

~~~powershell
& 'D:\RuntimeEnvironment\mise\mise\data\installs\python\3.12.13\python.exe' -I -B -X utf8 run_m7_offline_tests.py
~~~

所有实际argv、退出码、持续时间见 commands.json；build-results.json筛选compile/link/nm/analyze。
Core分translation unit编译再链接Host；不链接device/plugin/IOKit。
普通编译、链接、单元/差分/变异/分析进程退出码0；sanitizer canary的非零退出为预期检测。
CMake configure/build、MSVC、macOS native adapter及kext编译均NOT RUN。

## 8. 本阶段自动化测试结果

| 类别 | 本轮最后一次实际结果 |
|---|---|
| 原Python test_offline | 58项：56 PASS、2 SKIP；56内含4静态源码检查 |
| M6.5 Python回归 | 11 PASS |
| 新M7 Python | 22 PASS |
| 原C++回归 | 34 PASS |
| 新M7 C++ | 31 PASS |
| 差分 corpus | 743组，0差异 |
| 确定性变异 | 2400组，seed 759070，0差异 |
| ASan+UBSan | 新C++单元及3143组差分+变异；未发现诊断 |
| 检测器canary | heap-buffer-overflow / signed integer overflow均实际检测 |
| Clang静态分析 | 4个Core文件、0警告，非形式化正确性证明 |
| Core禁异常/RTTI与nm | PASS，编译flags及符号日志可复核 |
| Apple Kernel ABI / kext | NOT RUN |
| 真gfx1200 ELF | SKIP |
| 真GPU/显示/Vulkan/Metal | NOT RUN |

总Python 91项：89 PASS（含4静态检查）、2 SKIP；这些分类不重复计入行为测试。
C++共65项；差分和fuzz按输入计数，不与单元测试合成一个“总PASS”数字。
不统计历史M6.5结果为新增测试；不统计canary预期崩溃为普通测试失败。
数据均是合成/模拟，不能作为本机GPU实测E3。

测试串行、单进程30/40秒超时，输入有界，没有持续压力测试。
Sanitizer leak detection NOT VERIFIED；变异不是coverage-guided fuzz，不能证明穷尽恶意输入。

## 9. 保留的失败与修复记录

1. M7 runner wrapper漏掉stdin的第三位置参数，在差分入口TypeError。
   修正run(args,name,data=None,...)并改为显式safe日志写入；没有改解析器或测试期望。
2. 新合成ELF的额外section header覆盖旧NOTE布局，合法结构定向测试报out_of_bounds。
   将fixture NOTE移到文件尾，保持严格解析器检查与测试断言。
3. Manifest移入Core时，namespace外定义的Result返回类型未限定。
   修正为NaviCore::Result；严格编译门禁保持开启。

失败test-results/commands和编译、Python日志保存在execution/attempts。
没有关闭Sanitizer、降低检查或删失败路径。最终完整流水线已重新运行通过。

## 10. Darwin静态集成准备

实际Memory/Log/Snapshot契约与Host Mock已通过CPU行为测试。
native草案使用真实IOKit allocator/log/IOReturn接口，没有fake SDK；
guard只允许Apple KERNEL目标，且未加入Windowssource allowlist。
macOS build=NOT RUN，Node对象构造、输入retain、线程上下文、kernel栈和SDK符号仍为阻碍。
没有IOService/PCI probe/Bar mapping/device start；无驱动安装器或可加载产物。
详细生命周期和真实构建路线见docs/darwin-adapter-design.md、kernel-compatibility.md。

## 11. Cobalt/RADV/Metal准备增量

N44I v2 96B实际编解码、presence/保留字段/能力拒绝新增验证，不只是重复路线图。
它是CPU模拟协议：数据存在不等于硬件验证，capabilities=0、资源owner只记录政策。
静态阅读固定N48N QueryInfo 192B及Cobalt patch2/patch7实际函数与路径，
发现协议minor/内嵌头版本及canned gfx1201/GB_ADDR_CONFIG假设需要独立处理。
未应用Mesa patch、未连接IOUserClient、没有生产资源所有者或gfx1200 winsys。
更未建立Metal shader/AIR转换、资源/同步/呈现或WindowServer接入。
Metal-on-Vulkan与Vulkan-on-Metal不是同一方向；数据ABI不是任何一种加速实现。

## 12. 显示就绪度

当前只推进了CPU解析与软件接口。真实Navi44 Discovery/连接器/EDID/GOP/DMUB/DCN状态仍缺失。
已有edid.cpp纯逻辑可在下一轮CPU测试；硬件mode set、AUX、HDMI、VRAM/clock不能本轮运行。
2560×1440×4×180约2.65GB/s全屏单次写带宽，5.56ms帧时间，仅算术，不是性能实测。
模式扫描、合成性能和实际present帧率需分别验收，不能把显示画面当Metal兼容。

## 13. 安全记录

本代理所有主动文件输出限制在Lab；未执行Windows系统、EFI/BIOS/分区/SSD内容访问、
真实GPU、驱动加载、管理员提升、全局环境修改、远程代码推送或第三方部署脚本。
没有修改唯一RX9060XT的显示配置或硬件状态。
现有沙箱授权范围比Lab更广；Lab限制由路径校验、allowlist及人工审查补充。
未做独立系统级审计，不承诺OS缓存/日志或崩溃报告绝对零副作用。
详细审查见safety-audit.md，未解决边界见remaining-blockers.md。

## 14. 下一阶段与授权边界

| 类别 | 任务 | 所需额外条件与风险 |
|---|---|---|
| A Windows CPU-only | EDID/Atom表回归、CRC规范/格式扩展、metadata预算/性能、生产ABI候选映射、typed scratch接口 | 后续单独任务授权，仍只写Lab、不接设备；恶意输入资源受限 |
| B 真macOS构建 | Core Mach-O、native接口、SDK/符号/对象生命周期、合法gfx1200 code object、CPU测试 | 单独授权Mac工作区/编译；不等于允许加载、改安全策略或联网上传 |
| C 真GPU实验 | 本卡Discovery/连接器、GOP继承、DCN/DMUB、时钟/显存、输出恢复、VM/queue | 必须独立硬件授权与人工恢复；当前唯一显示GPU，黑屏/卡死风险高 |

生产驱动顺序：纯逻辑与合法样本 → 真macOS CPU编译 → 单所有者/生命周期 →
安全基础显示 → 显存/固件/队列隔离与恢复 → gfx1200命令 → RADV → Metal/系统合成。
本轮不自动进入任何下一阶段。未涉及macOS许可授权或为Apple Account生成身份。

## 15. 主要证据

E1官方规格/API；E2可审查源码；E3离线CPU运行日志（仅其测试范围）；E4作者自述；E5工程推断。
本文CPU结果为本轮真实进程输出，不是RX9060XT/macOS/GPU E3。

- [AMDRadeonRDNA4固定提交](https://github.com/RX4Darwin/AMDRadeonRDNA4.kext/tree/49f7f20c00dd154384418078f8a09e79c400a06a)：本地固定源码再次阅读，BSD-3-Clause，E2。
- [Cobalt64固定提交](https://github.com/Almosst-DEV/Cobalt64/tree/d6c9aedf8e6526a39e349b5886cbc8c7ddf77f65)：本地patch/N48N/Metal路径只读，许可证按文件，E2。
- [Linux firmware header](https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/amd/amdgpu/amdgpu_ucode.h)：2026-10-14网页读取，用于package结构交叉检查；master非固定快照，E2。
- [Apple XNU IOLib](https://github.com/apple-oss-distributions/xnu/blob/main/iokit/IOKit/IOLib.h)：2026-10-14读取真实接口，main非固定快照，E1/E2。
- [Lilu固定接口](https://github.com/acidanthera/Lilu/blob/0515f40b7f2a096adc85e832a4c6104fbd07f936/Lilu/Headers/kern_util.hpp)：2026-10-14网页读取，E2。
- [MacKernelSDK](https://github.com/acidanthera/MacKernelSDK)：真实内核头依赖参考；本轮未获取/构建pin，E2/NOT RUN。
- [LLVM ELF.h固定来源](https://github.com/llvm/llvm-project/blob/87f0227cb60147a26a1eeb4fb06e3b505e9c7261/llvm/include/llvm/BinaryFormat/ELF.h)：现有本地target枚举参考，E2。
- [LLVM-MinGW](https://github.com/mstorsjo/llvm-mingw/releases/tag/20261006)：既有工具归档；本轮只离线完整性验证。

GitHub精确raw URL部分抓取失败；固定仓库结论以已存在的本地pin源码为依据。
没有宣称追踪了最新主分支或证明所有社区功能可用于本卡。

## 16. 交付索引与最终状态

development-report.md：完整报告；baseline-results.json：独立基线；
test-results.json：本轮结果；build-results.json：编译细节；
commands.json：所有真实流水线argv/exit；execution/：原始日志与失败attempts；
changed-files.json：实际改动；deliverable-sha256.json：关键文件hash；
history-integrity.json：历史保留；toolchain-integrity.json：工具与已知归档一致；
delivery-verification.json：补丁校验/重放结果；patches/m7-from-m65.patch：增量代码与文档。

M7 CPU-only工程目标已完成。真实kext、显示、Vulkan与Metal仍未执行和验证。
未来工作等待独立授权，本轮交付后停止。
