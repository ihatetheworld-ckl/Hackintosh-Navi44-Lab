"""Checked documentation, manifests, incremental patch and CPU-only patch replay.
No build/install/GPU/network operation. All output paths checked against Lab.
"""
from pathlib import Path
import difflib,hashlib,json,os,subprocess,sys,zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m7_safety as safe
ROOT=safe.ROOT
OUT=ROOT/'reports/m7'
baseline=json.loads((OUT/'baseline-sha256.json').read_text())
results=json.loads((OUT/'test-results.json').read_text())
if results['status']!='PASS':raise SystemExit('Refusing final PASS report without passing execution')
commands=json.loads((OUT/'commands.json').read_text())
docs={
'docs/kernel-core-architecture.md':'''# M7 Core / Host / Darwin 架构

## 实际分层

~~~mermaid
flowchart LR
    W[Windows CPU tests / Python reference] --> H[Host compatibility / fixed mock]
    H --> C[Core: views, Result, bounded metadata, package, ABI]
    C --> P[Existing ASIC / Discovery / CodeObj pure logic]
    F[Future genuine Darwin build] --> D[Darwin native allocator/log/error draft]
    D --> I[Platform contract]
    I --> C
~~~

Core 包含 core/validation.hpp/.cpp、model.hpp、device_info.hpp/.cpp，以及继续复用的
src/asicprofile.hpp、ipdiscovery.cpp/.hpp、codeobj.cpp/.hpp。没有创建第二套 Discovery 解析器。
现有固件需求模型和状态机已移入 Core；旧 Offline::Session / State / FirmwareRequirement 是同一类型的别名。

Host 包含 host/validation_adapter.hpp、platform_mock.hpp、Python 参考、probe 和 tests。
src/offlinevalidation.cpp 是旧 API 的兼容转发层；其 MetadataBuffer 有较大的 Host 栈缓冲，未来内核不链接该文件。
STL/异常保留在 Host probe 与测试中，Core 源码不使用这些功能。

Platform contract 提供显式 MemoryOps / LogOps / SnapshotOps 与 Lease。
SnapshotKind 仅描述 CPU 文件输入，没有 BAR、MMIO、ROM、GPU queue 或 DMA API。
Darwin contract 可由 Host Mock 编译；darwin_native.cpp/.hpp 仅供真实 Apple Kernel SDK 的未来构建。

## 所有权与失败规则

- View 借用不可变 CPU 缓冲；调用方保证地址可访问、真实长度正确，并在整个解析过程保持存活。
- Scratch 使用调用方提供的 Node 数组。Core 不隐式分配，也不拥有输入。
- metadata 字符串借用输入；elf() 不返回节点或字符串，失败令 scratch.used=0。
- Package 的 payload View 会返回给调用方，生命周期不得超过原始输入；不是复制或固件许可。
- Result.detail 为内部静态诊断 token，offset 是输入偏移。并非任意用户字符串或硬件地址。
- Discovery 对象保存借用输入及条目偏移，必须与其源缓冲共同存活；旧对象布局不可视为稳定 ABI。
- Lease 禁止复制，校验 alignment，重复释放为空操作，释放后自身 view 清空。
  已复制出去的 View 不会自动失效；调用方不得在 close 后使用旧副本。
- Manifest / ABI / Package 验证失败会清空输出。OfflineReady 只代表离线流程完成。
- 输入完整性、CRC、PSP 签名和设备执行授权是不同条件。当前 capabilities 恒为 0，hardwareAllowed 恒 false。

## 限额

Host metadata scratch 512 节点；递归深度上限 16；容器计数上限 4096，节点索引小于 UINT16_MAX。
ELF 当前 PT_LOAD 虚拟范围上限为 16 MiB；这是既有实验性策略，并非通用 ROCm loader。
PSP package 最多 12 个已知类型；未知版本、重复类型、重叠、未支持 aux 和非零未验证 CRC 拒绝。
没有 runtime ABI 直接序列化 C++ 对象。N44I 使用显式 little-endian 字节读写。
''',
'docs/darwin-adapter-design.md':'''# M7 Darwin Adapter：实际接口与未验证源码

## 已有代码

platform/contract.hpp：显式分配/释放、结果日志、CPU Snapshot 借用、Lease。
host/platform_mock.hpp：固定 Node 数组、失败注入、分配/释放/日志计数；已在 Windows 运行测试。
platform/darwin_contract.hpp：不含 IOKit 的 AdapterDraft；硬件初始化恒 false。
platform/darwin_native.hpp/.cpp：真实 IOKit include、IOMallocAligned / IOFreeAligned、
IOLog 与 IOReturn 映射的静态草案；Windows 构建明确排除它们。
文件在非 Apple 或非 KERNEL 目标下显式 #error，不提供假的 Apple 类型。

## Kernel 生命周期契约

未来分配器最大 64 KiB、alignment 最大 4096。Lease 记录分配长度并使用匹配释放。
必须在可阻塞线程上下文调用，不能处于中断或 simple lock 临界区。
日志只输出内部 token / 错误码 / 输入 offset；不输出 PCI 物理地址、凭据或输入内容。
分配失败映射预算错误，日志不能成为 panic；未知验证错误映射参数错误。
这些映射是否符合目标 SDK 的 IOReturn、整数宽度、符号导出，需要真实编译确认。

重要未完成项：真实分配器必须明确提供 Node 数组对象生命周期。
Host Mock 自身持有活的 Node 数组；原始 IOMalloc 字节与 C++17 对象构造不能仅凭指针转换认为已解决。
首次 macOS 集成应采用目标 Kernel SDK 支持的 placement construction/对应释放，
或采用显式 typed-scratch 回调；同时验证错误与 teardown 路径。这是当前草案的阻碍。

输入缓冲必须由实际 OSData / IOMemoryDescriptor 的 retain/释放或独立拷贝保护，
但本轮没有实现对象包装、IOService probe/start/stop、IOPCIDevice 或 UserClient。
CPU Snapshot 接口不能自动升级为设备资源接口。
不新增资源探测、GPU 启动权限或安全开关。

## 证据与构建边界

Apple [IOLib.h](https://github.com/apple-oss-distributions/xnu/blob/main/iokit/IOKit/IOLib.h)
提供真实分配/释放及日志声明，并说明线程上下文限制（公开源码，2026-10-14 阅读，E1/E2）。
Lilu 固定 [kern_util.hpp](https://github.com/acidanthera/Lilu/blob/0515f40b7f2a096adc85e832a4c6104fbd07f936/Lilu/Headers/kern_util.hpp)
提供内核日志与 allocator 包装（E2）。本轮没有接入或调用这些第三方运行库。

Darwin native compile = NOT RUN；内核 ABI、符号解析、kext 链接及加载 = NOT RUN。
Host contract PASS 只证明纯 C++ callback 契约及模拟资源行为。
''',
'docs/kernel-compatibility.md':'''# M7 内核兼容性与真实 macOS 构建路线

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
''',
'docs/navi44-display-readiness.md':'''# M7 Navi 44 显示研发就绪度

## 确认与未知

用户确认 RX 9060 XT，PCI 1002:7590；现有 Asic profile 的 gfx1200 / GC 12.0.0 是家族预期。
Navi48 对照 gfx1201 / GC 12.0.1；不可将对照 ROM、固件、CU 数和寄存器常量复制成 Navi44 实测数据。
本轮没有读取本机 ROM、IP Discovery、PCI BAR、MMIO、EDID 或硬件电源状态。
所有当前自动化样本是合成数据；non-GC IP 版本和 topology 是刻意构造的测试值。

## 可复用源码位置（仅静态阅读）

src/ipdiscovery.cpp：版本、校验和、IP 与寄存器段地址解析；没有实际寄存器访问。
src/edid.cpp/.hpp：已有无 IOKit 的 EDID 纯逻辑，下一轮可加入 CPU allowlist 与恶意样本回归。
src/atombios.cpp：板卡连接器、固件表数据依赖，不能以其他板卡的样本代替本卡。
src/dmub.hpp、dptrain.cpp、dpphy.cpp、modeset.cpp、pipe.cpp、otgtiming.cpp、
ndrv.cpp：后续显示路径参考，当前没有编译/执行其硬件路径。

## 距基础输出仍缺少的具体条件

| 条件 | 当前状态 | 未来验收 |
|---|---|---|
| Navi44 真实 IP/拓扑与固件映射 | 缺少板卡样本 | 合法静态输入可重现解析；未知字段仍不可用 |
| GOP framebuffer 格式/stride/地址所有权 | 未确认 | 首先审查安全继承方案，证明不覆盖正在使用的平面 |
| EDID、连接器、DP AUX/HDMI DDC 与链路能力 | 未确认 | 先离线模式解析，再独立授权链路实验 |
| DCN/DMUB 与支持的精确 IP 版本 | 未确认板卡值 | 对比公开 amdgpu 接口，拒绝猜寄存器值 |
| 显存映射、firmware 状态、时钟与电源 | 未确认 | 单一资源所有者、超时、失败停止与恢复路径 |
| IONDRVFramebuffer / WindowServer 接入 | 未构建 | 真 macOS 编译，再独立 GPU 测试 |

本轮 Native adapter 只有 CPU 内存/日志接口，不能建立 framebuffer 输出。
基础显示、模式切换、热插拔、显示休眠、多屏、Metal 和 WindowServer 都是 NOT RUN。

## 1440p180 的量化边界

2560×1440×4 = 14,745,600 字节/完整 32bpp 帧；
180Hz 单次全屏写入约 2.65 GB/s（约 2.47 GiB/s），尚未计读回、alpha 合成及复制。
180Hz 帧时间约 5.56ms。这是纯算术下限，不是 GPU/CPU 测得性能。
有效像素约 663.6 Mpixel/s；链路还需要 blanking / encoding 与色深开销。
扫描输出速率、窗口合成速度、实际呈现帧率分别验收；解析通过不能证明任一项。

未来若丢失显示、DMUB 无响应、时钟/链路不一致或超时，立即停止后续初始化与提交，
不得循环重试猜测寄存器。软件恢复无法承诺恢复唯一显卡的黑屏，需额外人工恢复方案。
''',
'docs/cobalt-abi-readiness.md':'''# M7 Cobalt / RADV 数据接口准备

## 本轮实际增量

N44I v1 32B 保留。N44I v2 96B 增加版本化 presence、GC/topology、VRAM/BAR 大小、
固定 owner-policy 与保留字段；C++ encode/decode、Python decode、差分与错误拒绝测试已运行。
不是 N48N 生产协议，也没有 selector、IOUserClient、连接、队列或句柄。

| 字节 offset | 意义 |
|---|---|
| 0..7 | N44I、版本 2、长度 96 |
| 8..15 | vendor/device、revision/revisionKnown、gfx target |
| 16..19 | presence：1 GC、2 topology、4 memory；其余拒绝 |
| 20..23 | capabilities，必须为 0 |
| 24..27 | GC 三字节、reserved=0 |
| 28..47 | SE / CU / RB / TCC / GB_ADDR_CONFIG |
| 48..63 | 64位 VRAM bytes / visible BAR bytes |
| 64..67 | owner-policy=1：未来单所有者要求；不代表已实现资源所有权 |
| 68..95 | reserved=0 |

presence 只证明输入携带字段；不证明来自本机或硬件验证。profile.topology.verified 仍 false。
不存在实际 BAR 基址或任意物理地址。未知字段必须保持零，不生成 canned Navi48 能力。
GC/profile 不匹配、能力非零、reserved、尺寸、version、target 或范围不合法均拒绝并清空结果。

## 已阅读的具体上游位置

固定 AMDRadeonRDNA4 的 vulkan/navi48_native_abi.h：
N48N_SEL_QUERYINFO、n48n_info（192B）、GB_ADDR_CONFIG、GC、内存 pool、VMID、fence/VA 字段。
此头的 ABI minor 为 9，但 Cobalt 的 patch2 中内嵌头是较早协议；不能直接同名替换。

固定 Cobalt64 的 mesa-patches/0002-radv-Darwin-native-backend-Mesa-half-of-the-Navi48-k.patch：
src/amd/common/darwin/ac_darwin_{drm,iokit,kext,mock,sync}.c、
acd_native_handshake()、radv_physical_device.c 与 amdgpu winsys 修改位置。
这些是 patch 内真实路径；完整 Mesa checkout 当前不在项目中。
patch7 的 acd_native_handshake() 从 QueryInfo 取 GB_ADDR_CONFIG，但仍校验
ACD_GB_ADDR_CONFIG_GFX1201，并保留 ReadRegs fallback。Navi44 不能使用 override 让错误布局通过。
tools/native/navi48metal 与 src/xlat12 为 gfx1201 / Metal 实验参考，本轮不执行。

## 下一步（仍可 CPU-only）

建立 N44I → 候选查询结构的显式字段映射与合法版本协商测试；
先审核生产协议是否可包含 target/presence，而不是把 96B 直接 memcpy 到 192B。
取消 canned gfx1201 assumptions 的设计，需要真实 gfx1200 topology/GB_ADDR_CONFIG/firmware 依据。
未来 owner 接管 power/VM/BO/queues/display，用户态仅可受限 BO/submit/fence；
不得让 AMDRadeonRDNA4 与 Cobalt 双重初始化同一设备。
现在没有构造 Vulkan Device、RADV winsys 连接、Shader 执行或 Metal 能力。
'''}
for path,text in docs.items():safe.write(path,text)
safe.write('README.md','''# Hackintosh-Navi44-Lab

RX 9060 XT / Navi44 的 CPU-only 跨平台驱动研发实验室。
M7 已形成无 STL/异常的 Core、兼容 Host、Platform Mock 与 Darwin 静态接口；没有可部署驱动。

## 当前交付

- [M7 完整开发与测试报告](reports/m7/development-report.md)
- [M7 测试数据](reports/m7/test-results.json)
- [M7 真实命令与退出码](reports/m7/commands.json)
- [M7 安全审查](reports/m7/safety-audit.md)
- [M7 未解决事项](reports/m7/remaining-blockers.md)
- [Core 架构](docs/kernel-core-architecture.md)
- [Darwin 接口](docs/darwin-adapter-design.md)
- [内核构建边界](docs/kernel-compatibility.md)
- [显示就绪度](docs/navi44-display-readiness.md)
- [Cobalt ABI](docs/cobalt-abi-readiness.md)
- [M6.5→M7 源码与文档补丁](patches/m7-from-m65.patch)

## 当前 CPU-only 入口

仅在本项目根目录运行：

~~~powershell
& 'D:\\RuntimeEnvironment\\mise\\mise\\data\\installs\\python\\3.12.13\\python.exe' -I -B -X utf8 run_m7_offline_tests.py
~~~

复用项目中的便携 LLVM-MinGW；不改变 PATH、不安装依赖、不需要管理员。
日志 reports/m7/execution，构建 build/m7/execution，临时目录 tmp；单进程 30/40秒超时，测试串行。
M7 path guard 检查授权目录、reparse/link/hardlink 与父目录逃逸；不能代替 OS 沙箱或防止并发 TOCTOU。
Sanitizer canary 故意触发本项目 CPU 进程错误，非零退出用于证明检测器生效。

## 历史

[M6.5 报告](reports/m65-development-report.md)、reports/m65 与 M6 产物保留。
M7 改动前快照在 reports/m7/history，M7 基线复现在 reports/m7/baseline。
旧 run_all_offline_tests.py 主程序会写 M6.5 报告，不是 M7 入口，不应再执行。
M7 只复用其已审核的 helper 定义且重定向输出；不执行其 main。
m7_prepare.py / m7_refactor.py / core_model_m7.py 是一次性转换记录，非日常测试入口。
旧 docs/next-stage-readiness.md 等保留为 M6.5 状态，当前事实以 M7 文档为准。

Navi44 match / device init / Makefile 历史安全门禁保持原样，所有 GPU 能力保持关闭。
Darwin native / kext / GPU / Vulkan / Metal / EFI / 分区 / macOS 部署未执行。
''')

# Read-only Git evidence; no global config or hooks, no optional index locking.
env=os.environ.copy();env.update(GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='NUL',
                               TMP=str(ROOT/'tmp'),TEMP=str(ROOT/'tmp'))
git=Path('D:/RuntimeEnvironment/Git/cmd/git.exe')
git_results=[]
for folder in (ROOT,ROOT/'upstream/AMDRadeonRDNA4',ROOT/'upstream/Cobalt64'):
    args=[str(git),'-c','safe.directory='+str(folder),'-C',str(folder),'status','--short']
    p=subprocess.run(args,
                     env=env,capture_output=True,text=True,encoding='utf-8',timeout=15)
    git_results.append({'cwd':str(folder),'argv':args,'exit':p.returncode,
                        'stdout':p.stdout,'stderr':p.stderr})
safe.write(OUT/'git-status.json',json.dumps(git_results,ensure_ascii=False,indent=2))

# History artifacts stay byte-identical, irrespective of changed current source.
integrity={}
for rel,digest in baseline.items():
    original=ROOT/'reports/m7/history'/rel
    if hashlib.sha256(original.read_bytes()).hexdigest()!=digest:raise SystemExit('Snapshot altered: '+rel)
    if rel.startswith('reports/') and not rel.startswith('reports/m7/'):
        integrity[rel]=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==digest
if not all(integrity.values()):raise SystemExit('Historical artifact changed')
safe.write(OUT/'history-integrity.json',json.dumps({'status':'PASS','snapshot_files':len(baseline),
                                                'historical_reports':integrity},indent=2))

# Verify actual executable bytes against the already verified archive, without extracting.
toolchain=ROOT/'tools/toolchains/llvm/llvm-mingw-20261006-ucrt-x86_64'
archive=ROOT/'tools/toolchains/llvm-mingw-20261006-ucrt-x86_64.zip'
tool_hashes={}
with zipfile.ZipFile(archive) as z:
    for name in ('clang++.exe','llvm-nm.exe','llvm-symbolizer.exe','libclang_rt.asan_dynamic-x86_64.dll',
                 'libc++.dll','libunwind.dll','libwinpthread-1.dll'):
        actual=safe.checked(toolchain/'bin'/name)
        member='llvm-mingw-20261006-ucrt-x86_64/bin/'+name
        with z.open(member) as stream:expected=hashlib.file_digest(stream,'sha256').hexdigest()
        with actual.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if expected!=digest:raise SystemExit('Extracted toolchain differs: '+name)
        tool_hashes[name]=digest
safe.write(OUT/'toolchain-integrity.json',json.dumps({'status':'PASS','comparison':'existing verified ZIP; no extraction',
                                                 'sha256':tool_hashes},indent=2))

builds=[c for c in commands if c['name'].startswith(('compile-','link-','symbols-','analyze-'))]
safe.write(OUT/'build-results.json',json.dumps({'status':'PASS','compiler':(OUT/'execution/compiler-version.log').read_text(),
               'commands':builds,'windows_objects':'PE/COFF','Darwin_native':'NOT RUN','Kext':'NOT RUN',
               'CMake':'NOT RUN: static review only','MSVC':'NOT RUN','core_undefined':['memcpy','memset','internal Core references']},
               ensure_ascii=False,indent=2))
safe.write(OUT/'safety-audit.md','''# M7 安全审查与边界

## 授权及执行

唯一主动写入目录：D:/CodexWorkSpace/黑苹果研究/Hackintosh-Navi44-Lab。
使用现有 workspace-write 沙箱；沙箱允许范围比 Lab 更广，Lab 约束另由路径检查和固定 allowlist 执行。
没有请求 Full Access / 管理员 / require_escalated 或扩大权限。
路径检查拒绝 ..、越界 resolve、符号链接、NTFS reparse 与多硬链接；写入前核对现有父路径。
这不是独立 OS 审计，也不能证明竞态环境下绝对防逃逸。

本轮执行的进程：既有 Python、项目内已核对归档的 portable Clang / llvm-nm / symbolizer、
本项目 CPU-only exe、只读 Git status、工作区副本 Git apply 检查/重放。
网络仅使用网页阅读，不执行或克隆远程代码；上游脚本只读。
TMP/TEMP/CLANG_MODULE_CACHE_PATH 和 sanitizer log_path 指向 Lab；-B 禁止 Python pycache。
编译串行，测试进程有超时，固定 2400 次输入变异，不使用无限 fuzz 或 GPU benchmark。
运行前审查 source allowlist；Core/Host 不链接 device.cpp/plugin.cpp/IOKit。
宿主模型没有 PCI/BAR/MMIO/ROM/DMA/GPU Queue 方法。
Darwin native 文件从所有 Windows 编译入口排除，没有下载 Apple SDK 或构造替代头文件。

## 构建入口审查

CMake 只有显式 CPU source targets，未新增 install/FetchContent/ExternalProject/custom/pre/post build。
实际 runner 使用 subprocess argv，shell=False；没有远程脚本、包管理器、服务、驱动加载。
M7 重用本项目旧测试 helper，校验明确截断边界，不执行旧 main，不运行 git hook。
历史 fixture 必须存在，避免隐式重新生成。所有 M7 输出独立保存，重跑日志/失败 JSON 有 attempts 副本。
一次性源码转换脚本保留用于追溯，并在已转换/结构不符时拒绝再次应用。

## 执行记录声明

| 类别 | 本代理本轮执行记录 |
|---|---|
| 主动工作区外写入 | 未执行；没有独立系统级审计 |
| Windows 文件/注册表/服务/驱动/全局 PATH 修改 | 未执行 |
| EFI/BCD/BIOS/UEFI/Secure Boot/TPM/BitLocker 修改 | 未执行 |
| 磁盘分区或 Intel 256GB SSD 内容访问 | 未执行 |
| 真 GPU 访问、硬件 API、ROM/MMIO/BAR/固件/提交 | 未执行 |
| kext/SYS 加载与部署 | 未执行 |
| 管理员权限提升或未授权外部代码执行 | 未执行 |
| Git push / remote branch / PR / Release | 未执行 |
| CPU-only sanitizer canary | 已执行，仅故意使本项目子进程报告内存/整数错误 |

操作系统、运行库和 Codex 工具可能生成缓存、错误报告或日志，未做独立系统级观测，
因此不声称物理零写入或绝对零副作用。没有主动结束其他用户进程、重启或改变显示配置。
''')
safe.write(OUT/'remaining-blockers.md','''# M7 剩余阻碍

1. Darwin native 未编译；必须合法 Apple 编译环境。原始字节分配后的 Node 对象生命周期仍需实现和验证。
2. Windows Core flags 不等于 Darwin ABI；memcpy/memset 导出、递归总栈、SDK类型/符号与对象析构需核验。
3. CRC 非零仍拒绝；PSP signature 未验证，即使 package 结构 PASS 也不是可用固件。aux 非零不支持。
4. Manifest 是静态建议组件模型，不是完整生产固件 loader；Navi44 真实 non-GC IP、固件版本和板卡拓扑未知。
5. ELF relocation 只有结构检查，ALLOC relocation 拒绝；没有 relocation application、GPU ISA 验证或代码加载。
6. 真实编译产生的 gfx1200 ELF 缺失，便携编译器无 AMDGPU 后端；相关验证仍 SKIP。
7. N44I v2 presence 不是可信硬件有效位，capabilities 恒0。未接入生产 N48N、IOUserClient、BO/VM/fence。
8. DCN/DMUB/AUX/HDMI/GOP/显示恢复没有本机数据，也未进行 macOS framebuffer / WindowServer 测试。
9. RADV gfx1200 与 Cobalt gfx1201 假设不能直接互换；生产 ABI/资源所有者和 Metal 系统接入未实现。
10. Sanitizer 无报错只覆盖有限样本，Windows leak detection 未验证；非 coverage-guided fuzz，无并发/硬件稳定性证据。

没有因上述阻碍扩大权限。本轮开发停止在 CPU-only 工程交付。
''')

summary=f'''# M7 完整开发报告：RX 9060 XT / Navi 44

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
& 'D:\\RuntimeEnvironment\\mise\\mise\\data\\installs\\python\\3.12.13\\python.exe' -I -B -X utf8 run_m7_offline_tests.py
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
| 新M7 Python | {results['python']['test_m7.py']['PASS']} PASS |
| 原C++回归 | {results['cpp_regression']} PASS |
| 新M7 C++ | {results['cpp_m7']} PASS |
| 差分 corpus | {results['differential']}组，0差异 |
| 确定性变异 | {results['fuzz']['inputs']}组，seed {results['fuzz']['seed']}，0差异 |
| ASan+UBSan | 新C++单元及{results['sanitizers']['inputs']}组差分+变异；未发现诊断 |
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
'''
safe.write(OUT/'development-report.md',summary)

# Incremental text patch: existing baseline source/docs + newly authored source/docs.
# Never include historical snapshots, firmware, executables or sanitizer output as code patch.
existing=[rel for rel in baseline if not rel.startswith('reports/') and (ROOT/rel).is_file()]
new=[]
for folder in ('development/AMDRadeonRDNA4-Navi44/core','development/AMDRadeonRDNA4-Navi44/platform'):
    new += [p.relative_to(ROOT).as_posix() for p in (ROOT/folder).rglob('*') if p.is_file()]
new += ['development/AMDRadeonRDNA4-Navi44/host/platform_mock.hpp',
        'development/AMDRadeonRDNA4-Navi44/host/validation_adapter.hpp','tests/unit/m7_unit.cpp','tests/test_m7.py',
        'run_m7_offline_tests.py','m7_safety.py','m7_prepare.py','m7_refactor.py','core_model_m7.py','finalize_m7.py',
        *docs,'reports/m7/development-report.md','reports/m7/safety-audit.md','reports/m7/remaining-blockers.md']
changed=[]
pieces=[]
for rel in sorted(set(existing+new)):
    current=safe.checked(rel);data=current.read_bytes()
    old_path=ROOT/'reports/m7/history'/rel;before=old_path.read_bytes() if rel in baseline else b''
    if data==before:continue
    old_text=before.decode('utf-8').splitlines(keepends=True);new_text=data.decode('utf-8').splitlines(keepends=True)
    pieces.append('diff --git a/'+rel+' b/'+rel+'\n')
    if not before:pieces.append('new file mode 100644\n')
    pieces.extend(difflib.unified_diff(old_text,new_text,fromfile='a/'+rel if before else '/dev/null',tofile='b/'+rel))
    changed.append({'path':rel,'kind':'modified' if rel in baseline else 'added',
                    'before_sha256':hashlib.sha256(before).hexdigest() if before else None,
                    'after_sha256':hashlib.sha256(data).hexdigest()})
safe.write(OUT/'changed-files.json',json.dumps(changed,ensure_ascii=False,indent=2))
patch=safe.write('patches/m7-from-m65.patch',''.join(pieces))

# Replay patch solely into a fresh project-internal copy; never current source.
parent=safe.mkdir('build/m7/patch-replay');attempt=len(list(parent.iterdir()))+1
replay=safe.mkdir(parent/str(attempt))
for row in changed:
    if row['kind']=='modified':safe.write(replay/row['path'],(ROOT/'reports/m7/history'/row['path']).read_bytes())
checks=[]
for options in (['--check'],[]):
    # A fresh Lab-internal directory; no Git init, hooks or current-source mutation.
    args=[str(git),'-c','core.autocrlf=false','-c','core.whitespace=cr-at-eol','apply',*options,
          '--whitespace=nowarn',str(patch)]
    p=subprocess.run(args,cwd=replay,env=env,capture_output=True,text=True,encoding='utf-8',timeout=30)
    record={'argv':args,'cwd':str(replay),'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    checks.append(record);safe.write(OUT/('patch-'+('check' if options else 'replay')+'.log'),p.stdout+p.stderr)
    if p.returncode:raise SystemExit('Patch verification failed: '+p.stderr)
for row in changed:
    if hashlib.sha256(safe.checked(replay/row['path']).read_bytes()).hexdigest()!=row['after_sha256']:
        raise SystemExit('Patch replay byte mismatch: '+row['path'])
safe.write(OUT/'delivery-verification.json',json.dumps({'status':'PASS','changed_files':len(changed),
    'patch_sha256':hashlib.sha256(patch.read_bytes()).hexdigest(),'git_commands':checks,
    'replay_hashes':'all changed files match byte-for-byte','history':'PASS'},ensure_ascii=False,indent=2))
manifest={}
targets=[ROOT/row['path'] for row in changed]+[patch]+list(OUT.glob('*.json'))+list((ROOT/'build/m7/execution').glob('*.exe'))
for p in targets:
    if p.name=='deliverable-sha256.json':continue
    with p.open('rb') as stream:manifest[p.relative_to(ROOT).as_posix()]=hashlib.file_digest(stream,'sha256').hexdigest()
safe.write(OUT/'deliverable-sha256.json',json.dumps(manifest,ensure_ascii=False,indent=2))
print(json.dumps({'status':'PASS','changed_files':len(changed),'patch_sha256':hashlib.sha256(patch.read_bytes()).hexdigest(),
                  'history_files':len(baseline),'manifest_files':len(manifest),'report':str(OUT/'development-report.md')},ensure_ascii=False))
