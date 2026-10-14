"""Project-checked M8 reports, source patch, replay and hashes; no hardware."""
from pathlib import Path
import sys,json,hashlib,difflib,subprocess,os,zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m7_safety as safe
ROOT=safe.ROOT;OUT=safe.mkdir('reports/m8')
results=json.loads((OUT/'test-results.json').read_text())
if results['status']!='PASS':raise SystemExit('No final PASS without passing tests')
commands=json.loads((OUT/'commands.json').read_text())
before=json.loads((OUT/'baseline-sha256.json').read_text())
historical=json.loads((OUT/'historical-reports-sha256.json').read_text())
def digest(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
for rel,value in historical.items():
    if digest(safe.checked(rel))!=value:raise SystemExit('Historical report changed: '+rel)
for rel,value in before.items():
    if digest(OUT/'history'/rel)!=value:raise SystemExit('Snapshot changed: '+rel)
for name in ('device.cpp','plugin.cpp','asicprofile.hpp'):
    rel='development/AMDRadeonRDNA4-Navi44/src/'+name
    if digest(ROOT/rel)!=before[rel]:raise SystemExit('Historical hardware gate changed')
safe.write(OUT/'history-integrity.json',json.dumps({'status':'PASS','historical_files':len(historical),
           'snapshot_files':len(before),'GPU_gate_files':'unchanged'},indent=2))
env=os.environ.copy();env.update(GIT_CONFIG_GLOBAL='NUL',GIT_CONFIG_NOSYSTEM='1',GIT_OPTIONAL_LOCKS='0',
                               TMP=str(ROOT/'tmp'),TEMP=str(ROOT/'tmp'))
git=Path('D:/RuntimeEnvironment/Git/cmd/git.exe');git_results=[]
pins={'upstream/AMDRadeonRDNA4':'49f7f20c00dd154384418078f8a09e79c400a06a',
      'upstream/Cobalt64':'d6c9aedf8e6526a39e349b5886cbc8c7ddf77f65'}
for rel in ('.',*pins):
    folder=ROOT if rel=='.' else ROOT/rel
    for verb in (['status','--short'],['rev-parse','HEAD']):
        if rel=='.' and verb[0]=='rev-parse':continue
        args=[str(git),'-c','safe.directory='+str(folder),'-C',str(folder),*verb]
        p=subprocess.run(args,env=env,capture_output=True,text=True,encoding='utf-8',timeout=15)
        git_results.append({'argv':args,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        if rel in pins and (p.returncode or (verb[0]=='rev-parse' and p.stdout.strip()!=pins[rel])):
            raise SystemExit('Upstream Git evidence changed')
safe.write(OUT/'git-status.json',json.dumps(git_results,ensure_ascii=False,indent=2))
BIN=ROOT/'tools/toolchains/llvm/llvm-mingw-20261006-ucrt-x86_64/bin'
archive=ROOT/'tools/toolchains/llvm-mingw-20261006-ucrt-x86_64.zip'
expected=json.loads((ROOT/'reports/m65/toolchain-provenance.json').read_text())['expected_sha256']
if digest(archive)!=expected:raise SystemExit('Compiler archive mismatch')
toolhash={}
with zipfile.ZipFile(archive) as z:
    for name in ('clang++.exe','llvm-nm.exe','llvm-symbolizer.exe','x86_64-w64-windows-gnu.cfg','mingw32-common.cfg',
                 'libclang_rt.asan_dynamic-x86_64.dll','libc++.dll','libunwind.dll','libwinpthread-1.dll'):
        with z.open('llvm-mingw-20261006-ucrt-x86_64/bin/'+name) as stream:known=hashlib.file_digest(stream,'sha256').hexdigest()
        actual=digest(safe.checked(BIN/name))
        if actual!=known:raise SystemExit('Extracted tool differs: '+name)
        toolhash[name]=actual
safe.write(OUT/'toolchain-integrity.json',json.dumps({'status':'PASS','archive_sha256':expected,
           'method':'existing ZIP comparison, no download/extraction','sha256':toolhash},indent=2))

docs={
'docs/edid-parser-design.md':'''# M8 EDID Parser

继续复用 src/edid.cpp/.hpp 的字段、DMT/VIC表与CTA解码，没有增加第二套原始EDID解析器。
Core/display.cpp 提供严格的整包验证与 Mode/Monitor 模型，旧宽松诊断入口不能当生产能力验证。

支持范围：EDID 1.3/1.4，精确128字节块、Header、Checksum、manufacturer三字母编码/product，
最多基础块加3扩展；digital标志、progressive数字separate-sync DTD、
已有DMT的established/standard timing子集、CTA revision3的VIC表子集与DTD。
支持HDMI LLC/Forum VSDB的TMDS/SCDC声明字段；不控制SCDC，也不认为链路已训练。

新增严格拒绝：坏checksum/header/version、声明长度不一致、跨界DBC、非法DTD offset、
零offset却携带数据、短HDMI Forum block、重复vendor能力块、SVD容量耗尽、
sync超过blanking、零尺寸/宽度、超预算或不支持的signal。
源解析器的parseDetailedTiming失败清空结果；parseCtaBlock错误不返回部分成功。
Core edid()失败清空Monitor和调用方Mode存储。调用方保证输入、输出不重叠并存活。

不支持：EDID2、DisplayID、interlace/stereo/border/analog-composite DTD、完整HDR/FRL/DSC/VRR、
所有VIC、GTF/CVT公式。未知extension默认Unsupported；
KnownBlocksOnly策略仅保留已知块并标记partial；未解析的timing也计入unresolved/partial。
未知CTA vendor/extended payload不会被当作可用链路能力。
标准timing的DMT解析标记来源；Core不沿用EDID1.3“digital就支持RB”的隐式推断。

Mode.sources区分BaseDtd/CtaDtd/Established/Standard/CtaVic。
完全相同的raster、clock、sync、polarity去重并合并来源。
同尺寸同精确刷新率而timing不同，保留为sameRateAlternative，不能随意替换。
capacity不足返回Budget，不静默丢模式。hardwareVerified恒false。

测试fixture为自制合成字节，含规范中的1080p60 DTD数值；不是本机EDID，不包含用户serial。
所有扩展checksum校验。未通过DDC/I2C/AUX或Windows GPU API查询显示器。

格式参考：
[VESA E-EDID A2](https://glenwing.github.io/docs/VESA-EEDID-A2.pdf)，2006规范公开镜像；
[Linux v6.15 drm_edid.c](https://github.com/torvalds/linux/blob/v6.15/drivers/gpu/drm/drm_edid.c)，
对照DTD/CTA边界和HF块最小长度（2026-10-14阅读，E1/E2）。
没有复制Linux实现或引入其运行库。
''',
'docs/atombios-parser-design.md':'''# M8 AtomBIOS Static Parser

在原AtomBios类上加固，Core connectors()转发到它，不创建重复ROM解析器。
支持静态55AA legacy image、512B块长度、镜像sum8、
ATOM ROM header2.2/2.3已知前缀、master data table2.1的35个entry、
display object info1.5 path_v3（16B）、I2C与HPD静态records和DP/HDMI等connector类型。
读取的是调用方不可变CPU字节，不执行command bytecode。

镜像输入最大4MiB，在512B边界扫描；遇到带签名但无效的image停止，不自动绕过损坏主镜像。
读表范围限定选中的legacy image，不允许借更大的外层buffer逃逸。
验证ATOM/master header长度版本、表offset/common size、表间/控制表重叠、自引用与重复alias。
路径最多8个、storage不超8个；connector重复/错误对象类型/reserved/path count拒绝。
record不得指向path array；每步至少2B、最多128步、必须终止；重复I2C/HPD和非法size拒绝。
unknown record仅按长度有限跳过，不解释为PHY支持。USBC特殊reserved配置当前拒绝，保留为未支持。
输出先暂存，成功后commit；失败清空ConnectorList/paths。借用ROM仅存在于Parser对象寿命内。

修正master table枚举：DCE index27、VRAM28、VoltageObject32，
由AMD公开atomfirmware.h的v2.1字段顺序核对。Display v1.4 path_v2不再混作v1.5。
其他table只验证通用边界，不宣称完整字段语义或所有ATOM版本兼容。
legacy checksum不是固件真实性或PSP签名认证。

不支持完整PCI PCIR多image链验证、完整PSP包/ROM board authentication、
其他display object版本、encoder/PHY实际routing、GPIO寄存器使用、执行ATOM函数。
没有读取本机ROM，也未使用其他板卡ROM映射冒充Navi44结果。
真实Navi44 VBIOS与connector routing = UNVERIFIED；本轮数据全部合成。

[AMD atomfirmware.h](https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/amd/include/atomfirmware.h)
用于布局交叉检查，2026-10-14阅读，master为移动参考；
已有AMDRadeonRDNA4源码commit49f7f20c为工程基础（E2）。
文件头既有Navi48验证描述属于上游历史，不是本轮、本机测试声明。
''',
'docs/navi44-display-capability.md':'''# M8 Display Capability / Mode / Link Model

~~~mermaid
flowchart LR
    E[EDID CPU bytes] --> M[Monitor declarations / Modes]
    R[Static Atom ROM bytes] --> C[Connector descriptions]
    M --> A[Pure mathematical assessment]
    C --> F[Future connector / PHY adapter: not implemented]
    L[Independent link budget] --> A
    G[Independent engine budget] --> A
    A --> U[No output permission / no hardware verified capability]
~~~

核心函数：NaviDisplay::timing、edid、connectors、assess。
Mode包含完整DetailedTiming、约分后的64位refresh fraction、source与同频替代标志。
Monitor包含mfg/product、digital、partial、声明的TMDS/SCDC与计数，不包含用户serial。
Connector包含原object/encoder/tag、静态I2C/HPD记录；routingKnown/boardVerified均false。

Origin = Unknown / Synthetic / StaticReference，只记录来源声明，不是认证。
没有从字节数据产生DeviceVerified的枚举值。不能伪装本机测试。
输入/输出缓冲由调用方持有，不应相互重叠；Core无IO或隐式allocation。

数学规则：geometry/sync与blanking一致，progressive，clock范围1000..2500000kHz，
刷新率实验预算1..1000Hz。它们是本原型预算，不是AMD/DP的正式最大能力。
refresh = pixelClockKHz×1000 / (hTotal×vTotal)，64位整数约分。
判断RGB24/30/36bpp；DP8b10b只接受已知lane数1/2/4与1.62/2.7/5.4/8.1Gbps；
payload按8/10计算。TMDS假设RGB/4:4:4，payload=characterClock×24，深色占用更高。
引擎clock单独比较。未知证据不产生WithinBudget。
WithinBudget只代表理想算术上限，未计算完整protocol/audio/control/FEC/blanking分配，也不是链路可用证明。
不支持UHBR128b132、HDMI FRL、DSC、YCbCr subsampling、VRR或训练。
任何结果outputAllowed/hardwareVerified始终false。

frameBytes=activeW×activeH×4；fullFrameBytesPerSecond为按刷新分数计算的向上取整写带宽。
乘法溢出直接拒绝。timing()复制输入后清空输出，支持input与out.timing别名的再验证。

## 1440p180

2560×1440×180=663552000有效像素/秒，尚未计消隐。
经典EDID DTD的16位10kHz clock上限655350kHz，低于该数值；
因此不能用经典DTD表达本目标，必须进一步研究DisplayID/其他合法表达。
本轮DisplayID不支持，不能宣称已解析本显示器180Hz。
合成模型2720×1500 totals / 734400kHz严格算得180Hz，只用于数学测试，不是实际输出参数建议。
32bpp完整帧14745600B，180fps一次写带宽2654208000B/s、帧时间约5.56ms。
没有GPU/CPU性能测量，扫描速率、合成与实际present帧率需各自未来验收。
''',
'docs/darwin-adapter-m8.md':'''# M8 Darwin Adapter contract

沿用MemoryOps / LogOps / SnapshotOps / Lease；新增ScratchOps / ExecutionOps，
SnapshotOps增加成对release。旧raw MemoryOps继续只服务原始字节；解析器不再将raw分配cast为Node。

Host Mock从对齐uint8_t数组改为真正的Node[512]，修正M7未解决的C++对象生命周期问题。
NodePool也直接持有构造好的Node数组；nativeScratchOps只引用调用方构造的pool，
不依赖伪造的placement-new/SDK，不暗中分配或操作设备。
Kernel pool应随长期owner对象存活、放在堆/owner成员中，不能放入kernel栈。

validateSnapshot顺序：ExecutionOps.enter → borrow input → acquire live Nodes →
Core validate → release Nodes → release input → log → ExecutionOps.leave。
失败/无scratch/解析拒绝均按RAII配对释放；缺失context或lifetime callback时拒绝。
Mock测试了parser失败、资源不足、错误上下文、重入与missing release。
Mock的inCall/busy是串行模拟，不是原子锁。NodePool不是thread-safe，
真实Darwin adapter必须提供线程上下文与正确的serialization/teardown，不能把bool当内核锁。

日志仅内部静态token/输入offset，不输出物理地址、serial或payload。
callbacks是可信adapter契约：不能抛异常、访问硬件或在中断中调用可阻塞分配/日志。
跨callback重入和异步销毁的真正kernel实现仍NOT RUN。
借用View副本不会自动失效；owner必须保持输入、context和callback lifetime。

只静态阅读：
[固定MacKernelSDK IOService.h](https://github.com/acidanthera/MacKernelSDK/blob/05094e5e88cec7caedbfb35e8449ed0db94bf95b/Headers/IOKit/IOService.h)
的probe/start/stop/open/close/handleOpen及arbitration语义；
[Apple OSObject](https://github.com/apple-oss-distributions/xnu/blob/main/libkern/libkern/c++/OSObject.h)
的retain/release与并发限制；
[IOLib](https://github.com/apple-oss-distributions/xnu/blob/main/iokit/IOKit/IOLib.h)线程上下文要求。
这不等于实际IOService包装或引用计数已经接入。
pin IOLib/IOPCIDevice部分网页抓取失败；未下载SDK替代或伪造类型。
Darwin native build、kext link/load、PCI binding均NOT RUN。
''',
'docs/cobalt-production-abi.md':'''# M8 Cobalt Production ABI candidate

新增core/query_candidate.hpp/.cpp，在现有N44I v2上加N44Q 1.0 envelope。
128B explicit little-endian，不直接序列化C++结构，不是生产N48N协议。

| offset | 内容 |
|---|---|
| 0..3 | N44Q |
| 4..9 | major1/minor0/length128 |
| 10..11 | reserved0 |
| 12 | provenance Unknown/Synthetic/StaticReference |
| 13..15 | verification/owner state/reserved，均0 |
| 16..19 | presence，必须与内嵌N44I一致 |
| 20..23 | verified capabilities，必须0 |
| 24..31 | 非零generation（CPU会话epoch，不是本机身份） |
| 32..127 | 既有N44I v2 96B |

未知version/minor/length、false verification、owner、capability、provenance或presence不匹配拒绝。
来源标签不是硬件真实性证明。字段存在不意味着topology/GB_ADDR_CONFIG等已在本机验证。
encode先写局部缓冲并validate，再commit；decode失败清空模型。

OfflineOwner是纯CPU单对象lease状态机：单lease、generation递增、stale token使状态失败终止，
close后借用失败。canInitializeHardware恒false，不能仲裁真实GPU或两个独立驱动实例。
无IOUserClient、selector、MMIO、物理地址、queue或GPU资源句柄。

固定源码审查：
- AMDRadeonRDNA4 vulkan/navi48_native_abi.h为N48N minor9。
- Cobalt src/navi48-bringup/src/Navi48NativeABI.h为minor12，QueryInfo192B；
  v1.10在reserved区引入session VRAM budget，v1.11/12引入scanout selectors22..26。
- native_open_policy_pure.h：root/WindowServer/APP角色、route和selector限制，
  APP不得ReadRegs/scanout；import-caller必须匹配owner task。
- native_g4_pure.h：session memory budget、映射回收等工程条件。
- mesa-patches/0002、0007：Darwin transport与QueryInfo/GB_ADDR_CONFIG路径。

上述是本地固定commit的可读实现，不是本机复现；没有执行upstream脚本或bring-up。
不能将ABI1.9/1.12头按名字混用，不能把N44Q128B复制到N48N192B。

生产差距：可信内核采样来源、真实owner exclusivity、权限认证、task lifetime、
BO/VM/fence、可撤销映射、reset/poisoning与caps协商、gfx1200 shader及Mesa winsys。
未来由单一驱动拥有power/firmware/VM/queues/display；其他模块仅通过受限接口调用，
不允许AMDRadeonRDNA4与Cobalt双重初始化。N44Q不授予任何硬件权限。
''',
'docs/macos-build-readiness.md':'''# M8 macOS Build Readiness / M9

Windows已真实编译：既有ASIC/Discovery/CodeObj/validation/device_info，
新增EDID/AtomBIOS/display/integrity/query_candidate及不含Apple SDK的Platform contract。
9个Core translation unit使用C++17、-fno-exceptions、-fno-rtti、-ffreestanding、
-Wall/-Wextra/-Werror和4096B单函数栈警告，并审查object undefined symbols。
仍有memcpy/memset和内部Core引用。总递归栈、Mach-O、Apple symbol/ABI仍未验证。
Host tests/STL/exception wrapper不进入kernel target；Darwin native不进入Windows target。

~~~mermaid
flowchart TD
    A[合法Xcode / Apple SDK / fixed KernelSDK] --> B[真实macOS Core compile only]
    C[Explicit CPU source list / no hardware backend] --> B
    B --> D[Mach-O symbol / layout / stack check]
    D --> E[CPU fixture / lifetime tests on macOS]
    E --> F[Darwin thread / OSData ownership wrapper review]
    F --> G[未来独立kext build授权]
    G --> H[未来独立load / hardware授权]
~~~

M9建议优先真实macOS的CPU编译与纯逻辑测试，而不是先堆积寄存器初始化：
1. 用户明确指定合法、已具备Xcode/SDK的Mac及授权工作区；本轮不自动连接。
2. 只编译Core和adapter object，确认真实头、固定宽度、missing symbols、constructor/teardown。
3. 复跑同一合成fixtures和CPU-only测试；不签名、不安装、不加载kext。
4. 解决NodePool堆生命周期、OSData/descriptor retain、ExecutionOps gate和kernel stack预算。
5. 再研究kext target与版本适配；独立授权不可由此自动获得。

AMDRadeonRDNA4固定Makefile参考macOS11 ABI。MacKernelSDK pin
05094e5e88cec7caedbfb35e8449ed0db94bf95b；Lilu pin0515f40b7f2a096adc85e832a4c6104fbd07f936。
固定SDK README基于macOS11/Xcode12.0头，不能推出新Xcode/Sequoia/Tahoe实际兼容。
没有Windows交叉kext build、fake Apple SDK、自动上传或远程CI。
KernelSDK native/object compile = NOT RUN；kext build/load = NOT RUN。

若暂时没有合法Mac，Windows仍可针对DisplayID、真实合法静态样本、Atom其他版本、
CRC格式来源、parser budget继续有限研发；这些不能替代真实Darwin构建。
'''}
for path,text in docs.items():safe.write(path,text)
safe.write('README.md','''# Hackintosh-Navi44-Lab

RX 9060 XT / Navi44 的 CPU-only 驱动研发工作区；当前阶段 M8。
已形成 EDID / AtomBIOS 静态解析与显示预算模型，没有可部署驱动或真实显示输出。

## 当前交付

- [M8完整报告](reports/m8/development-report.md)
- [测试结果](reports/m8/test-results.json)
- [真实命令/退出码](reports/m8/commands.json)
- [安全审查](reports/m8/safety-audit.md)
- [剩余阻碍](reports/m8/remaining-blockers.md)
- [增量源码补丁](patches/m8-from-m7.patch)
- [EDID设计](docs/edid-parser-design.md)
- [AtomBIOS设计](docs/atombios-parser-design.md)
- [Display模型](docs/navi44-display-capability.md)
- [Darwin契约](docs/darwin-adapter-m8.md)
- [Cobalt候选ABI](docs/cobalt-production-abi.md)
- [真正macOS构建路线](docs/macos-build-readiness.md)

## CPU-only测试入口

仅在本项目目录运行：

~~~powershell
& 'D:\\RuntimeEnvironment\\mise\\mise\\data\\installs\\python\\3.12.13\\python.exe' -I -B -X utf8 run_m8_offline_tests.py
~~~

使用已有便携Clang，无系统安装/管理员/全局PATH修改。
reports/m8/regression/execution存日志，build/m8存产物，tmp存临时文件。
串行有限测试；子进程30/40秒超时。canary是仅项目子进程的预期CPU错误。
CMake已更新显式CPU目标与超时，但本轮未configure/build，不应写到Lab外。

M8改动前关键快照reports/m8/history，独立M7基线reports/m8/baseline。
M7/M6.5/M6历史报告与补丁保留，不再运行旧stage主入口或finalizer覆盖历史记录。
M8只读旧helper定义并重定向输出；m8_prepare/harden/baseline_retry为一次性追溯脚本。
平台path guard不是独立OS沙箱，实际沙箱授权更宽；每次写入仍限制在Lab。
GPU match/init/Makefile禁用，Host不链接device/plugin/native IOKit。
没有实际GPU、Vulkan/Metal、WindowServer、kext、EFI、SSD或macOS部署。
''')
safe.write(OUT/'safety-audit.md','''# M8 安全审查

唯一主动写入边界：D:/CodexWorkSpace/黑苹果研究/Hackintosh-Navi44-Lab。
已确认当前workspace-write沙箱允许范围比Lab更广，不宣称OS级Lab专属隔离。
人工审查每个命令，固定源码/进程allowlist，写入前执行真实路径/父目录检查；
拒绝..、越界resolve、symlink/reparse/junction与多hardlink。不能抵御独立并发TOCTOU攻击。
无法确认安全的设备/SDK/远程操作没有执行；没有请求Full Access或权限提升。

实际进程：既有Python、Lab中核对过归档的Clang/nm/symbolizer、本项目CPU-only exe、
只读Git status/rev-parse、项目副本Git apply。没有执行上游完整构建/安装脚本。
M8 runner从旧runner明确边界导入已审查helper，重定向所有M7输出，
不执行旧report writer。历史文件hash核对，最终验证旧gate源码字节未改。
Host源码只列Core与EDID/Atom纯解析，排除device/plugin/IOKit/native GPU API。

TMP/TEMP/cache及sanitizer日志指向Lab，Python -B。每子进程30/40秒，串行固定种子，
fuzz有限2400+800，已有变异2400，非无限/性能压力。一个16MiB+1测试buffer用于budget边界，
不通过放宽Host1MiB传输限制完成差分。失败保留于attempts，不关闭Sanitizer。
只有本项目canary进程发生预期异常；未结束用户其他进程。
CMake显式CPU source、无fetch/install/custom/pre/post hooks；新增CTest串行30秒。
CMake/MSVC/native SDK构建未执行。compiler CFG与runtime重新对照已有ZIP。

| 禁止操作 | 本代理执行记录 |
|---|---|
| 工作区外主动写入 | 未执行；无独立系统级审计 |
| Windows系统/注册表/服务/驱动/安全策略修改 | 未执行 |
| EFI/BCD/BIOS/UEFI/TPM/Secure Boot/BitLocker修改 | 未执行 |
| SSD分区/Intel第二盘内容访问 | 未执行 |
| GPU BAR/MMIO/ROM/VBIOS/DMA/固件/命令 | 未执行 |
| DDC/I2C/AUX或显示配置变更 | 未执行 |
| SYS/Kext注册/加载/安装 | 未执行 |
| 管理员/全局PATH/Git配置 | 未执行 |
| 未授权远程设备/代码推送/PR/Release | 未执行 |
| 远程第三方代码执行/系统安装 | 未执行 |

网络仅网页阅读；未下载/运行新工具链、Apple SDK或上游脚本。
操作系统和工具可能产生缓存、日志、故障报告，未有独立系统级观测，
因此不承诺物理零写入或绝对零副作用。
''')
safe.write(OUT/'remaining-blockers.md','''# M8 剩余阻碍

- DisplayID未实现；经典EDID DTD clock无法表达1440p180，不能宣称本监视器完整解析。
- EDID只支持1.3/1.4及CTA rev3子集；interlace/stereo/FRL/DSC/HDR/VRR/完整VIC仍未支持。
- Atom只支持限定header/master/display版本与静态记录，没有真实Navi44 ROM或PHY routing证据。
- 原始checksum/静态元数据不是固件签名或真实硬件能力证明。
- CRC-32 ISO-HDLC算法已实现，但AMD固件具体格式/convention缺少可信样本确认，默认拒绝路径不放宽。
- ELF只有离线验证/预算，没有GPU loader/ISA执行；真gfx1200编译产物继续SKIP。
- Node对象生命周期已通过typed pool改造；真实Darwin OSData retain/线程gate/heap pool/teardown仍未接入。
- native Apple API源码未编译，Windows COFF检查不能替代Mach-O、内核符号/总栈/SDK兼容。
- N44Q是数据候选，无真实IOUserClient认证或全局GPU owner；N48N1.9与Cobalt1.12不能混用。
- GPU power/firmware/DCN/DMUB/GOP/AUX/VM/queue/恢复完全未执行；显示/Vulkan/Metal/WindowServer NOT RUN。
- Sanitizer只覆盖有限输入，leak/concurrency/hardware stability没有验证，fuzz非coverage-guided。

M9优先真实macOS CPU编译/fixture验证；随后再判断是否有条件进行独立kext或硬件研发。
不存在本轮授权可自动启动的GPU实验或Mac远程操作。
''')
reg=results['regression'];pyPass=sum(x['PASS'] for x in reg['python'].values())+results['python_m8']['PASS']
cppOld=reg['cpp_regression']+reg['cpp_m7']
summary=f'''# M8 完整开发报告：Navi 44 显示核心与Darwin就绪工程

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
& 'D:\\RuntimeEnvironment\\mise\\mise\\data\\installs\\python\\3.12.13\\python.exe' -I -B -X utf8 run_m8_offline_tests.py
~~~

所有实际argv、exit、持续时间见commands.json；构建详情见build-results.json。
普通compile/link/unit/diff/fuzz/analyze exit0；canary非零为预期检测。
CMake修改后静态审查显式source与CTest timeout，现有Safety tests重新通过；
实际CMake configure/build、MSVC/native SDK均NOT RUN。

## 11. 自动化结果（最后一次执行）

| 分类 | 结果 |
|---|---|
| 原Python回归 | 89 PASS、2 SKIP；89中4项静态检查 |
| 新PythonM8 | {results['python_m8']['PASS']} PASS |
| 原C++回归 | {cppOld} PASS（34+31） |
| 新C++M8 | {results['m8_cpp']} PASS |
| 共享差分 | 743原corpus+{results['budget_differential']}新预算=744组，零差异 |
| 原确定变异 | 2400组，seed759070，零差异 |
| 新EDID/ROM变异 | 2400组，seed759080，invariants PASS |
| 新query变异 | 800组，同一PRNG续序，invariants PASS |
| Sanitizer | 原3143 corpus/变异、新3200变异及M7/M8单元均通过当前覆盖 |
| 检测器canary | heap-buffer-overflow/整数溢出实际检测 |
| 静态分析 | 10文件零warning |
| Core flags / object symbols / contract | PASS |
| 真ROM/EDID、gfx1200ELF、Darwin/Kext/GPU | UNVERIFIED/NOT READ/SKIP/NOT RUN |

Python总{pyPass} PASS、2SKIP；C++总{cppOld+results['m8_cpp']} PASS。
不把基线额外复现、重复sanitizer执行、truncate循环输入和静态assert再计入新单元数量。
原差分与新fuzz不是同一种验收，不能拼出“GPU支持总PASS”。
新模块不强行重复写Python Parser，以固定规范值、C++行为与Sanitizer验证。

~~~text
{results['m8_fuzz']}
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
'''
safe.write(OUT/'development-report.md',summary)
builds=[c for c in commands if any(c['name'].startswith(t) for t in ('compile-','link-','symbols-','analyze-','m8-compile-','m8-link-','m8-symbols-','m8-analyze-','m8-contract-'))]
safe.write(OUT/'build-results.json',json.dumps({'status':'PASS','compiler':(OUT/'regression/execution/compiler-version.log').read_text(),
           'commands':builds,'CMake':'NOT RUN: static review','MSVC':'NOT RUN','Darwin_native':'NOT RUN','Kext':'NOT RUN'},
           ensure_ascii=False,indent=2))

# m8_prepare was created before its own snapshot; it is still new versus M7.
new_stage={'m8_prepare.py','m8_baseline_retry.py','m8_harden_parsers.py','run_m8_offline_tests.py','finalize_m8.py',
           'tests/test_m8.py','tests/unit/m8_unit.cpp','tests/unit/m8_fuzz.cpp','tests/unit/m8_contract_compile.cpp',
           'tests/fixtures/m8_display.hpp',*docs,'reports/m8/development-report.md',
           'reports/m8/safety-audit.md','reports/m8/remaining-blockers.md'}
for folder in ('development/AMDRadeonRDNA4-Navi44/core','development/AMDRadeonRDNA4-Navi44/platform'):
    new_stage.update(p.relative_to(ROOT).as_posix() for p in (ROOT/folder).rglob('*') if p.is_file())
existing={r for r in before if not r.startswith('reports/') and not r.startswith('patches/') and r!='m8_prepare.py'}
changes=[];pieces=[]
for rel in sorted(existing|new_stage):
    p=safe.checked(rel)
    if not p.is_file():continue
    data=p.read_bytes();old=(OUT/'history'/rel).read_bytes() if rel in existing else b''
    if data==old:continue
    pieces.append('diff --git a/'+rel+' b/'+rel+'\n')
    if not old:pieces.append('new file mode 100644\n')
    pieces.extend(difflib.unified_diff(old.decode('utf-8').splitlines(keepends=True),
                 data.decode('utf-8').splitlines(keepends=True),fromfile='a/'+rel if old else '/dev/null',tofile='b/'+rel))
    changes.append({'path':rel,'kind':'modified' if old else 'added',
                    'before_sha256':hashlib.sha256(old).hexdigest() if old else None,'after_sha256':hashlib.sha256(data).hexdigest()})
safe.write(OUT/'changed-files.json',json.dumps(changes,ensure_ascii=False,indent=2))
patch=safe.write('patches/m8-from-m7.patch',''.join(pieces))
folder=safe.mkdir('build/m8/patch-replay');replay=safe.mkdir(folder/str(len(list(folder.iterdir()))+1))
for row in changes:
    if row['kind']=='modified':safe.write(replay/row['path'],(OUT/'history'/row['path']).read_bytes())
records=[]
for flags in (['--check'],[]):
    args=[str(git),'-c','core.autocrlf=false','-c','core.whitespace=cr-at-eol','apply',*flags,'--whitespace=nowarn',str(patch)]
    p=subprocess.run(args,cwd=replay,env=env,capture_output=True,text=True,encoding='utf-8',timeout=30)
    records.append({'argv':args,'cwd':str(replay),'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    safe.write(OUT/('patch-check.log' if flags else 'patch-replay.log'),p.stdout+p.stderr)
    if p.returncode:raise SystemExit('Patch failure: '+p.stderr)
for row in changes:
    if digest(safe.checked(replay/row['path']))!=row['after_sha256']:raise SystemExit('Replay mismatch: '+row['path'])
safe.write(OUT/'delivery-verification.json',json.dumps({'status':'PASS','changed_files':len(changes),
           'patch_sha256':digest(patch),'git':records,'replay':'all changed files byte-identical','history':'PASS'},ensure_ascii=False,indent=2))
targets=[ROOT/r['path'] for r in changes]+[patch]+list(OUT.glob('*.json'))+list((ROOT/'build/m8/execution').glob('*.exe'))
manifest={p.relative_to(ROOT).as_posix():digest(safe.checked(p)) for p in targets if p.name!='deliverable-sha256.json'}
safe.write(OUT/'deliverable-sha256.json',json.dumps(manifest,ensure_ascii=False,indent=2))
print(json.dumps({'status':'PASS','changed_files':len(changes),'manifest_files':len(manifest),
                  'historical_files':len(historical),'patch_sha256':digest(patch),'report':str(OUT/'development-report.md')},ensure_ascii=False))
