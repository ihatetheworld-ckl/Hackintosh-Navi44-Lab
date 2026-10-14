"""Local-only report and patch generator. No external processes or networking."""
from pathlib import Path
import difflib
import hashlib
import json
ROOT=Path(__file__).resolve().parent
DEV=ROOT/'development/AMDRadeonRDNA4-Navi44'
UP=ROOT/'upstream/AMDRadeonRDNA4'

def write(path,text):
    p=ROOT/path
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(text,encoding='utf-8',newline='\n')

pins={
 'date':'2026-10-13 Asia/Shanghai',
 'AMDRadeonRDNA4':{'url':'https://github.com/RX4Darwin/AMDRadeonRDNA4.kext','commit':'49f7f20c00dd154384418078f8a09e79c400a06a','current_main_same':True,'license':'BSD-3-Clause'},
 'Cobalt64':{'url':'https://github.com/Almosst-DEV/Cobalt64','commit':'d6c9aedf8e6526a39e349b5886cbc8c7ddf77f65','current_main_same':True,'top_license':'MIT; file/subdirectory licenses differ'},
 'Cobalt_PR12':{'state':'open/unmerged','head':'2c3bba7771ed0d51dc01a6882987a4cfbbd1afe2','code_not_applied':True},
 'LLVM':{'tag':'llvmorg-20.1.8','commit':'87f0227cb60147a26a1eeb4fb06e3b505e9c7261','reference':'upstream/references/llvm-ELF.h'},
 'Linux':{'commit':'24a19b953e2a3d0ea5a8c4951a0ab8f32720c907','reference':'upstream/references/linux-discovery.h'},
 'Mesa':{'cobalt_patch_base':'f5cb8ee032adabef599ae892ec4e42d796b84da9','full_repo_downloaded':False},
 'tools':{'Python':'3.12.13','Git':'2.55.0.windows.4','C++':'not found','CMake':'not found','macOS SDK':'not available'},
 'fixtures':'synthetic only; no RX9060XT capture; no real firmware/shader',
}
pins['reference_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'upstream/references').iterdir() if p.is_file()}
write('reports/provenance.json',json.dumps(pins,ensure_ascii=False,indent=2))

paths=['Makefile','src/asicprofile.hpp','src/offlinefirmware.hpp','src/plugin.cpp','src/device.cpp',
       'src/codeobj.hpp','src/codeobj.cpp','src/ipdiscovery.hpp','src/ipdiscovery.cpp','host/navi44.py']
patch=[]
changes=[]
for path in paths:
    old=UP/path; new=DEV/path
    a=old.read_text(encoding='utf-8').splitlines(keepends=True) if old.exists() else []
    b=new.read_text(encoding='utf-8').splitlines(keepends=True)
    if a != b:
        changes.append(path)
        patch.extend(difflib.unified_diff(a,b,fromfile='a/'+path if old.exists() else '/dev/null',tofile='b/'+path))
write('patches/navi44-offline-prototype.patch',''.join(patch))
write('reports/changed-files.json',json.dumps(changes,indent=2))

write('README.md','''# Hackintosh-Navi44-Lab

实际的 RX 9060 XT / Navi 44 **离线适配原型**。不能安装、加载或用来启动 macOS。

## 已实现

- C++ ASIC profile：7590/gfx1200 与 7550/7551/gfx1201 区分，revision 显式记录。
- 上游 C++ code object 校验参数化；旧调用默认 gfx1201。
- 上游 Discovery 边界、表 checksum、重复 IP、地址溢出与状态清理改进。
- Python host library：32/64-bit Discovery、profile、firmware manifest、ELF/metadata、状态机、ABI。
- CPU-only 测试、补丁、来源及验收报告。

## 安全范围

没有硬件访问后端。Python 不导入 GPU/driver/FFI 库。CMake 只链接纯解析代码。
Navi44 不进入实际设备匹配；init 的硬件授权恒为 false，且所有上游 Makefile 目标被禁用。
完整上游包含危险硬件工具，**仅作资料，不要执行其脚本**。

## 实际运行方法

在本目录使用现有 Python，不安装依赖：

```powershell
& 'D:\\RuntimeEnvironment\\mise\\mise\\data\\installs\\python\\3.12.13\\python.exe' -I -B run_offline.py
```

也可运行 `build_offline.ps1 -PythonExe <现有Python的绝对路径>`；它将进程 TMP/TEMP 指到 lab/tmp 并恢复。
报告输出只在 reports/。`-I -B` 隔离用户 Python 环境，并禁止 pyc 写入。

## 当前验证范围

见 [实际测试结果](reports/test-results.md)、[开发报告](reports/implementation-report.md) 和 [阻碍](reports/remaining-blockers.md)。
Python 测试不证明 C++ 编译、Kext、GPU、Metal 或 WindowServer 已工作。
真实 fixture 与真正 shader 编译产物缺失明确 SKIP。

## 目录

upstream/ 为固定参考；development/ 为修改副本；tests/、build/、docs/、patches/、reports/、tmp/ 均在独立工作区。
`tools_integrate.py` 是一次性已审查的源转换记录；不需要重复执行，不是安装器。
`finish_reports.py` 只生成本地补丁和文档，不访问网络或执行其他工具。

许可证：新增代码采用上游 BSD-3-Clause；参考项目分别保留许可证。详见 docs/architecture.md。
''')

docs={
'architecture.md':'''# 架构与实现范围

固定 AMDRadeonRDNA4 49f7f20、Cobalt64 d6c9aed。主线复查均与此前版本一致；PR12 仍未合并，未应用。

实际数据流：PCI/profile → Discovery → firmware requirements/结构检查 → OfflineReady。
ELF target 校验独立用于验证未来输入；N44I 数据协议仅为模拟接口。

C++ 与 Python 是两个实现，不声称 Python 测试覆盖 C++。C++ 传统 IpEntry 是 uint32_t bases，64-bit 格式明确拒绝；Python 完整保留64-bit地址。
纯 C++ host target 只包含 codeobj.cpp/ipdiscovery.cpp 和测试，不链接 device.cpp/plugin.cpp/IOKit。

新增文件 BSD-3-Clause，原 LICENSE 保留。Linux discovery.h 的 AMD MIT 声明保留；LLVM ELF.h 原声明保留。Cobalt 顶层 MIT、子目录及依赖需分别审计。本阶段不复制或分发 AMD 固件与 Apple 私有框架。

完整 kext 尚未编译。上游 snapshot 不变；开发副本中 Makefile 全部目标被禁用。init 对所有 ASIC 默认拒绝，故它不能当 Navi48 可部署版本。Navi48 的纯识别/默认 shader target 保留。
''',
'navi44-profile.md':'''# Navi44 Profile

1002:7590 → Navi44/gfx1200；1002:7550/7551 → Navi48/gfx1201。未知 vendor/device 拒绝。
revision 可 absent 或明确 0..255；没有实机 revision allowlist，所以 revisionVerified 恒为 false。
GC12.0.0/12.0.1 是上游家族的预期值，不是本机捕获。

C++ topology 全为 0 且 verified=false，零代表 Unknown，不是实际无 CU；Python 不提供活跃 CU/RB/TCC/BAR。
GC_INFO 的 SE/RB 是输入描述，不能当实际启用 topology。capabilities 全为空/零。
identify 与 driver bind 分离：Navi44 match hook 明确 false；任何 OfflineReady 都不授权硬件初始化。
''',
'firmware-and-discovery.md':'''# Discovery 与固件

格式依据固定 Linux discovery.h。Python 支持 binary v1.0..1.3/v2.0、IPDS v3/v4、单 die、32/64位 base；其他版本拒绝。
验证 binary/table checksum、表不重叠、声明长度、die、IP/base 数量、重复实例、地址乘4溢出。
未知 IP 保留为 unknown_ids，不赋予能力；GC 版本需匹配 profile。GC_INFO 仅支持基础1.0/2.0，并验证最小完整结构。

上游 C++ parser 加固基本边界/checksum/重复与寄存器溢出，但保持32-bit公开接口，明确拒绝64-bit格式；尚无编译/真实 fixture 回归。

Firmware Manifest 根据输入 IP 生成组件需求，不把 Navi48 固件赋给 Navi44。PSP/SMU/SDMA/DCN 的本机版本未知。
组件清单是研发需求模型，不能当已验证固件加载顺序；各子版本组件规则、PSP package v2/更高格式还需适配。
当前仅支持 common header v1.0；验证长度、payload、IP major/minor、重复与缺失。非零 CRC 明确 CrcUnverified 而非跳过后成功；没有 signature 验证、上传或真实固件。
测试 fixture 中的非GC版本、SE/RB与payload均是合成示例，不是RX9060XT数据。
''',
'gfx1200-target.md':'''# gfx1200 / ELF

固定 LLVM llvmorg-20.1.8：commit 87f0227cb60147a26a1eeb4fb06e3b505e9c7261。
upstream/references/llvm-ELF.h 核验 gfx1200=0x048、gfx1201=0x04e。

C++ CodeObj::parseImage/findKernel 新增 expected 参数，默认 Gfx1201 保留原调用；Unknown 与交叉 target 拒绝。
Python 校验 ELF64 little endian、AMDGPU、ET_DYN、表边界、PT_LOAD、SHT_NOTE、AMDGPU type32及必需metadata子集。
MsgPack parser 有深度/数量/边界/重复键限制，未支持编码明确拒绝。要求版本、非空kernel、name/symbol/kernarg size。
这不是完整 AMDHSA metadata 验证，也不保证 descriptor/symbol 与所有代码语义一致。C++旧loader并未得到完整新metadata校验，Python与C++范围不同。
不重标记shader、不编译AMDGPU、不提交GPU。真正产物测试SKIP。
''',
'safety-boundaries.md':'''# 安全边界

本阶段仅授权项目内源码、CPU-only测试和报告。没有EFI/分区/注册表/驱动/显卡状态变更授权。

1. 编译隔离：CMake仅列纯解析源文件；没有硬件后端、IOKit、Vulkan、DX/OpenCL或FFI。
2. 运行门禁：hardwareInitializationAllowed 恒 false；无命令行/boot arg 能使其变真。init入口拒绝；7590不绑定。
3. 构建门禁：开发Makefile直接报错，不允许上游kext/硬件工具目标。
4. 工具隔离：新脚本仅标准库；-I -B；TMP/TEMP指向lab/tmp；无全局配置修改、hook/submodule执行、安装与push。

源码门禁不是OS沙箱。本会话有workspace-write权限，其允许范围大于lab，不能声称建立了新的OS级lab沙箱。下载在网络授权进程中完成，未请求管理员权限；所有显式写入目标在lab。
Git safe.directory 仅进程命令参数用于已知克隆目录，没有global git config写入。
普通OS/网络缓存不可承诺绝对零写入。
仓库旧脚本保留作参考，含硬件/安装代码，未运行。不要手动绕过门禁。
''',
'cobalt-integration-plan.md':'''# Cobalt / RADV 后续接口

Navi48NativeABI.h 当前拥有QueryInfo、BO、CTX、Submit/Wait及ScanX等selector。不能把版本字串改成Navi44后直接使用。
本原型N44I wire v1为32 bytes little-endian：magic、version、size、vendor/device、revision、revision有效标志、target、capabilities=0、reserved=0。
没有transport、IOUserClient或selector，更不是N48N兼容ABI。未知active topology不编码，显式拒绝；decode对version/size/target/capabilities拒绝。

后续：真实内核profile→可信IP/topology/VRAM/BAR/GB_ADDR_CONFIG查询→版本化ABI→Darwin RADV。
需传SE/CU/RB/TCC与有效位，不能用canned gfx1201填Navi44。Mesa补丁基础f5cb8ee032adabef599ae892ec4e42d796b84da9，未下载完整Mesa或运行它。
VMID生命周期、BO隔离、提交fence必须由单一GPU owner管理。PR12仍未合并；其Metal bundle版本与公开主线差异需先解决。
Metal/WindowServer依赖真实macOS、私有ABI、shader cache/转译、共享纹理等，未实现。不能同时绑定两套GPU内核驱动。
'''
}
for name,text in docs.items(): write('docs/'+name,text)

result=json.loads((ROOT/'reports/test-results.json').read_text(encoding='utf-8'))
write('reports/test-results.md',f'''# 实际离线测试结果

日期：2026-10-13。Python 3.12.13，CPU-only，无第三方依赖。

| 状态 | 数量/范围 |
|---|---|
| PASS | {result['PASS']} 项真正执行的Python测试 |
| FAIL | {result['FAIL']} |
| SKIP | {result['SKIP']}：真实Navi44 Discovery、真正shader产物缺失 |
| NOT RUN | C++编译、macOS Kext构建、全部硬件功能 |

总数 {result['tests']}。包括1000次确定性输入变异、所有截断长度、多类错误输入、profile/firmware/ELF/ABI和失败状态。

实际命令：`& 'D:\\RuntimeEnvironment\\mise\\mise\\data\\installs\\python\\3.12.13\\python.exe' -I -B run_offline.py`
完整日志：[test-log.txt](test-log.txt)，机器可读：[test-results.json](test-results.json)。
Python测试不证明C++正确；输入变异不是完整fuzz覆盖；所有fixture均合成。
''')
write('reports/remaining-blockers.md','''# 未完成与阻碍

1. 未找到现有C++ compiler/CMake，没有安装任何依赖；C++代码未编译、未运行，待独立环境验证。
2. 无Apple SDK/真实macOS，Kext未构建。
3. 没有Navi44真实Discovery/VBIOS/topology/BAR/revision/EDID；无MMIO/ROM读取。
4. C++legacy接口拒绝64-bit bases；完整64-bit到Darwin接口还需设计，不截断。
5. Firmware组件清单未实机确认；common header仅v1.0、CRC非零拒绝；PSP签名、组件header和实际blob仍未验证。
6. Python metadata仅子集，C++旧loader尚未完整对齐；真正gfx1200编译产物缺失。
7. 显示、模式切换、命令提交、Vulkan/Metal/WindowServer全未实现/验证本机。
8. Cobalt私有ABI、bundle52/公开20、shadercache复现问题未解决；PR12未应用。
9. OS sandbox不能仅由源码建立；未来硬件实验必须单独授权、工具审查、备份和人工恢复能力。

下一阶段可先补C++离线编译和交叉语言fixture、完整metadata/firmware版本、parser fuzz，仍不碰GPU。
走向真实显示需要合法macOS工具链、板卡数据和明确实机授权；不会自动开始。
''')
write('reports/implementation-report.md',f'''# 实际开发交付报告

## 1. 进度

M0已创建独立目录、克隆并固定源码；M1已实现profile；M2已实现host parser/firmware模型及C++加固；M3已参数化C++target并实现host ELF校验；M4已加门禁并实际运行CPU测试；M5已实现模拟ABI；M6已生成补丁、日志和报告。
这些均为离线软件成果。C++及完整Kext未编译，硬件部分未完成。

## 2. 环境

目录：`D:\\CodexWorkSpace\\黑苹果研究\\Hackintosh-Navi44-Lab`。
Python3.12.13；Git现有工具；没有可用C++/CMake/Apple SDK。固定来源见 [provenance.json](provenance.json)。
首个sandbox网络请求失败，网络授权后仅clone/text下载；没有管理员权限请求。未安装工具，未改global PATH/Git。

## 3. 开发副本修改

'''+'\n'.join('- `'+p+'`' for p in changes)+f'''

`tests/test_offline.py`、`tests/fixtures/synthetic.py`、`tests/unit/host_tests.cpp`、`run_offline.py`、`build_offline.ps1`、`CMakeLists.txt`及docs/reports为新增交付。
上游参考快照不修改。开发副本包含原LICENSE，原危险工具未运行。

## 4. 原型实现

PCI/ASIC/revision/target描述；未知能力关闭；profile与绑定分离；Discovery版本/checksum/边界；firmware需求与结构校验；ELF目标与metadata子集；失败状态；N44I模拟协议。
详见docs。本原型没有硬件后端，不是可加载驱动。

## 5. 实际测试

{result['PASS']} PASS、{result['FAIL']} FAIL、{result['SKIP']} SKIP，合计{result['tests']}。见 [测试报告](test-results.md)。
C++/Kext/真实GPU为NOT RUN，不能用Python PASS替代。

## 6. 质量与限制

当前C++改动未经编译；parser/firmware/metadata支持范围有限；真实fixture缺失；需进一步交叉实现回归、fuzz和安全审计。
所有合成拓扑与非GC版本明确不是本机参数；不公开未验证硬件功能。

## 7. 功能等级

| 功能 | 实际状态 |
|---|---|
| PCI/Profile | Python离线PASS，C++源码完成未编译 |
| Discovery | Python32/64离线PASS；C++加固未编译，64明确拒绝 |
| Firmware | 合成manifest/结构PASS，真实固件未验证 |
| gfx1200 | 离线目标校验PASS，真正shader未验证 |
| 基础显示 | NOT RUN，未部署 |
| GPU提交/Vulkan/Metal/WindowServer | NOT RUN，未接入 |

## 8. 后续

先补现有合法C++工具链与纯fixture测试，再考虑完善固件/metadata/64位接口。显示与GPU实机需另行授权，不能由本报告自动进入。

代码与补丁：[navi44-offline-prototype.patch](../patches/navi44-offline-prototype.patch)。
''')

manifest={}
for rel in ('development/AMDRadeonRDNA4-Navi44/src/asicprofile.hpp','development/AMDRadeonRDNA4-Navi44/host/navi44.py','tests/test_offline.py','patches/navi44-offline-prototype.patch'):
    manifest[rel]=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
write('reports/artifact-sha256.json',json.dumps(manifest,indent=2))
print('Generated patch, provenance, six docs and reports; changed upstream files:',len(changes))
