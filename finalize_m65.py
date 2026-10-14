"""M6.5 project-local documentation/patch finalization. No build/device calls.
Reads actual results; preserves M6 historical reports and old documentation.
"""
from pathlib import Path
import difflib
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parent
DEV = ROOT/'development/AMDRadeonRDNA4-Navi44'
UP = ROOT/'upstream/AMDRadeonRDNA4'
HISTORY = ROOT/'reports/m65/history'
R = json.loads((ROOT/'reports/m65/results.json').read_text(encoding='utf-8'))
if R.get('status') != 'PASS':
    raise SystemExit('Finalization requires a successful complete pipeline record')
for rel, expected in R['source_sha256'].items():
    if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() != expected:
        raise SystemExit('Source changed after recorded tests: '+rel)

def write(rel, text, preserve=False):
    path = ROOT/rel
    if not path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('Output outside lab')
    if preserve and path.exists():
        old = HISTORY/rel
        if not old.exists():
            old.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, old)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')

base = json.loads((HISTORY/'baseline-sha256.json').read_text(encoding='utf-8'))
historical_checks = {}
for rel in ('reports/test-results.json','reports/test-log.txt','patches/navi44-offline-prototype.patch'):
    historical_checks[rel] = hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() == base[rel]
if not all(historical_checks.values()):
    raise SystemExit('M6 historical artifact unexpectedly changed')

# A cumulative patch against the immutable upstream, and a separate M6->M6.5
# patch for the lab. Binary regression is generated from included synthetic.py.
development_paths = ['Makefile','src/asicprofile.hpp','src/offlinefirmware.hpp','src/plugin.cpp',
    'src/device.cpp','src/codeobj.hpp','src/codeobj.cpp','src/ipdiscovery.hpp',
    'src/ipdiscovery.cpp','src/offlinevalidation.hpp','src/offlinevalidation.cpp','host/navi44.py']
def difference(old, new, name):
    before = old.read_text(encoding='utf-8').splitlines(keepends=True) if old.exists() else []
    after = new.read_text(encoding='utf-8').splitlines(keepends=True)
    if before == after: return ''
    return ''.join(difflib.unified_diff(before, after,
        fromfile='a/'+name if old.exists() else '/dev/null', tofile='b/'+name))
cumulative = ''.join(difference(UP/p,DEV/p,p) for p in development_paths)
write('patches/navi44-m65-offline-cumulative.patch', cumulative)
project_paths = ['CMakeLists.txt','run_all_offline_tests.py','finalize_m65.py','validate_m65_delivery.py',
    'm65_prepare.py','m65_acquire_toolchain.py',
    'm65_replace_discovery.py','tests/test_m65.py','tests/fixtures/synthetic.py',
    'tests/unit/m65_unit.cpp','tests/unit/m65_probe.cpp','tests/unit/sanitizer_canary.cpp',
    'tests/unit/sanitizer_smoke.cpp']
project_paths += ['development/AMDRadeonRDNA4-Navi44/'+p for p in development_paths
                 if p not in ('Makefile','src/plugin.cpp','src/device.cpp')]
delta = ''.join(difference(HISTORY/p,ROOT/p,p) for p in project_paths)
write('patches/m65-from-m6-offline.patch', delta)
changes = []
for p in project_paths:
    old = HISTORY/p
    if not old.exists() or old.read_bytes() != (ROOT/p).read_bytes():
        changes.append({'path':p,'type':'modified' if old.exists() else 'added',
                        'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()})
write('reports/m65/changed-files.json',json.dumps(changes,ensure_ascii=False,indent=2))
write('reports/m65/history-integrity.json',json.dumps(historical_checks,indent=2))

readme = '''# Hackintosh-Navi44-Lab

RX 9060 XT / Navi 44 原生 macOS 项目的 **CPU-only 离线适配原型**。
当前已完成 M6.5 Windows C++ 编译、跨语言比较及 ASan/UBSan 验证；没有可部署 kext。

## 本轮交付

- [M6.5 完整开发报告](reports/m65-development-report.md)
- [编译结果](reports/m65-build-results.md)
- [测试结果](reports/m65-test-results.md)
- [安全审查](reports/m65-security-review.md)
- [未完成项](reports/m65-remaining-blockers.md)
- [机器可读结果](reports/m65/results.json)
- [M6→M6.5 补丁](patches/m65-from-m6-offline.patch)
- [上游累计补丁](patches/navi44-m65-offline-cumulative.patch)

## 实际实现

ASIC/profile；32/64 位 Discovery；旧 32 位接口溢出拒绝；firmware common header/需求模型；
ELF、metadata、kernel descriptor 一致性；模拟 N44I ABI；状态顺序与默认禁止硬件初始化。
严格校验 host 层使用 STL/异常，不能直接视为 macOS 内核兼容实现。

## 统一入口

在本项目目录，使用现有 Python：

```powershell
& 'D:\\RuntimeEnvironment\\mise\\mise\\data\\installs\\python\\3.12.13\\python.exe' -I -B -X utf8 run_all_offline_tests.py
```

便携 Clang 位于 tools/toolchains/llvm/，无系统安装、PATH 修改或管理员权限。
入口依次执行 Python、C++ 编译/单元测试、静态分析、差分、受控变异、sanitizer 与预期失败 canary。
日志只在 reports/m65，构建产物只在 build/m65，临时目录在 tmp。
Canary 的非零退出是预期 CPU 内存错误检测，不是普通测试失败。

## 历史与禁用范围

M6 原报告和补丁保留；基线快照在 reports/m65/history。
run_offline.py / finish_reports.py / tools_integrate.py 为历史入口或转换记录，不是当前统一入口；
不要再次执行会覆盖 M6 报告的历史生成器。
完整上游含硬件与安装脚本，仅作参考，不执行。
Navi44 不绑定；所有设备 init 恒拒绝；开发 Makefile 仍禁用；host 构建不链接 IOKit/device/plugin。
GPU、EFI、BIOS、磁盘分区、驱动加载及 macOS 安装均未执行。
'''
write('README.md', readme, preserve=True)

docs = {
'architecture.md': '''# 当前架构：M6.5

固定 AMDRadeonRDNA4 49f7f20、Cobalt64 d6c9aed；不因本轮收尾宣称上游状态更新。

```text
allocation-free core: asicprofile / IpDiscovery / CodeObj
                     ↓
host validation: firmware / ELF metadata / descriptor / ABI / state
                     ↓
Windows CPU-only unit / probe → Python canonical comparison

macOS / IOKit / MMIO / submit adapters: future, NOT RUN
```

IpEntry 旧布局保留；新增 IpEntry64 和 initBinary 精确解析；init 保留离线 ROM 扫描。
IpDiscovery 类的内部大小改变，未来 macOS 使用者必须全部重新构建，不能假设二进制 ABI 不变。
Discovery 是调用者不可变内存的 view，调用者必须维护有效期；不读真实 ROM。
offlinevalidation.cpp 的 STL/异常属于 host 层，不可直接放入禁异常、无 libc++ 的 kext。
纯逻辑代码已真实 Windows 编译，但 macOS ABI/SDK 编译没有验证。

新增代码 BSD-3-Clause；原 LICENSE 保留。工具链各组件许可证保留；没有复制私有 Apple 框架或真实固件。
硬件 init 对所有 ASIC 恒拒绝，因此本分支也不是可直接部署的 Navi48 驱动。
''',
'firmware-and-discovery.md': '''# Discovery / Firmware：M6.5

格式依据固定 Linux discovery.h。binary v1.0..1.3/v2.0，IPDS v3/v4，单 die；其他版本拒绝。
Python 与 C++ 使用相同的合成输入，比较 header/IP/版本/base/GC_INFO/拒绝原因。
32/64 位 base 都保留；新增 ipAt64/findIp64/regByteOffset64。
旧 IpEntry 为 uint32_t，只有值可表示才返回；高位不会静默截断。
base 是寄存器 segment 的 dword 基址，byte offset 转换检查乘法/加法，不等于 PCI BAR/物理地址。

FirmwareRequirements 已有 C++ 模型，核对 ASIC/GC、所需 IP、拓扑描述缺失；仍是 advisory 组件清单。
GC_INFO SE/RB、非GC IP 版本和固件 payload 均来自合成输入，不代表本机。
Common header 仅 v1.0；大小、payload、major/minor、允许的组件声明检查已测试。
common header 不编码完整 revision/组件身份，sidecar 声明不是实际组件内容认证。
非零 CRC 明确 firmware_crc_unverified；未猜测 AMD CRC 覆盖范围或伪报签名验证。
PSP v2/package/真实加载顺序等尚未支持。没有下载、解析真实 GPU 固件或上传。
''',
'gfx1200-target.md': '''# gfx1200 / ELF：M6.5

固定 LLVM ELF.h 核验 gfx1200=0x048、gfx1201=0x04e；不重标记二进制。
保留 CodeObj 的 expected 参数与旧默认 gfx1201。

新增 C++ Offline::elf / elfKernel，与 Python validate_elf / validate_kernel 独立实现并差分。
先检查完整 section file envelope，再 metadata，再符号和 descriptor，避免损坏结构诊断顺序不一致。
校验 ET_DYN/AMDGPU、target、PT_LOAD、section/note、UTF-8/MsgPack 子集、metadata 版本1.0..1.2、
name/symbol/kernarg、选定 kernel 的 descriptor entry 与符号、kernarg/group/private 大小一致性。
CodeObj 修复有符号 entry 偏移溢出/下溢，并拒绝 NOBITS 当作文件代码。

严格 host API 没有自动接入现有 kext 的全部 loader 调用；完整 relocations/AMDHSA/shader 语义仍未覆盖。
完整 synthetic kernel ELF 是格式测试数据，不是 AMD 指令或编译产物。
已下载工具链没有 AMDGPU backend，真正 gfx1200 产物测试仍 SKIP；不运行 GPU API。
''',
'safety-boundaries.md': '''# 安全边界：M6.5

项目内写源码和 CPU-only 测试获授权。没有系统、驱动、启动、安全策略或真实 GPU 实验授权。
Clang/LLD/runtime 仅便携解压到 lab；无安装器、注册表、全局 PATH 或管理员权限操作。
host source 列表只含解析、校验和测试；没有 device.cpp/plugin.cpp/IOKit、Vulkan、DX、OpenCL。
Navi44 不绑定；hardwareInitializationAllowed 恒 false；开发 Makefile 保持禁用。

测试用固定种子、有限输入（当前最大约1200 bytes）、单个顺序 probe、30 秒执行 timeout、60 秒编译 timeout。
没有声明额外的 OS Job 内存配额或专属 lab 沙箱；不穷举/无限 fuzz、不占用 GPU。
ASan/UBSan canary 是自有 CPU 进程的故意错误；仅用于验证检测器，非正常数据 PASS。
LeakSanitizer 未验证，detect_leaks=0；检测通过不证明全代码无内存漏洞。
系统/网络的正常日志缓存不能承诺物理零写入。项目没有执行磁盘/硬件访问审计，不能作绝对安全证明。
''',
'cobalt-integration-plan.md': '''# Cobalt / RADV 接口准备：M6.5

N44I v1 为32字节little-endian，C++/Python已有离线验证：magic/version/length、PCI、revision有效位、target、
capabilities=0、reserved=0；未知能力不得发布。没有transport/IOUserClient/selector，非生产N48N ABI。
gfx1200/gfx1201可共享版本化查询协议，但ASIC/IP/topology/固件需求必须独立，不能使用canned gfx1201。

未来可信内核profile→带有效位的真实GC/SE/CU/RB/TCC/GB_ADDR_CONFIG/VRAM/BAR→生产ABI→Darwin RADV。
IP寄存器基址不应混入BAR物理地址字段；没有任意MMIO或物理地址操作接口。
单一驱动拥有GPU power/VM/queue/display，用户态只通过受限BO/submit/fence访问。
VMID生命周期、BO隔离、复位和并发需要未来单独验证，本轮没有实现真实资源所有权。
Cobalt PR12、bundle/cache和私有Metal接入仍是此前固定研究状态，未应用/运行。
''',
'cross-language-parser.md': '''# 跨语言差分验证

Python生产参考函数和C++真实编译probe分别读取相同bytes；C++不调用Python也不复制其输出。
canonical JSON比较接受/拒绝、binary/IPDS版本、地址宽度、IP实例/版本/base、GC_INFO；
另比较profile、firmware结构/需求、ELF/descriptor与N44I。
错误码在共同支持格式内也需一致；Unsupported不是假PASS。
537个共享case在 reports/m65/shared-corpus.json；多数为截断/错误输入，不等于537份实机fixture。
2400次seed759065变异同样比较，两实现最终零差异；尚未使用coverage-guided libFuzzer。
地址高位用JSON整数精确保留，避免浮点路径。
回归m65-invalid-strtab.bin：合成kernel ELF字符串表声明越界，源生成规则在synthetic.py/统一入口。
''',
'cpp-host-build.md': '''# Windows C++ host构建

便携LLVM-MinGW 20261006 UCRT x86_64，Clang23.1.3；官方release asset SHA256记录在toolchain-provenance.json。
包含C++库、mingw-w64头/import库、LLD和compiler-rt，不需要安装Windows SDK/VS。
项目路径：tools/toolchains/llvm/llvm-mingw-20261006-ucrt-x86_64/。

```powershell
& 'D:\\RuntimeEnvironment\\mise\\mise\\data\\installs\\python\\3.12.13\\python.exe' -I -B -X utf8 run_all_offline_tests.py
```

实际直接clang++编译，C++17、-Wall -Wextra -Werror、-static -g -O1；完整argv在commands.json。
sanitized增加-fsanitize=address,undefined -fno-omit-frame-pointer。
ASan DLL还依赖libc++/libunwind；仅复制已校验包内DLL到build/m65，不写Windows。
ASAN_OPTIONS的log_path使用项目相对路径，避免盘符冒号被误解析。
stdio显式UTF-8，TMP/TEMP与Clang cache在项目内。
CMakeLists保留CPU-only source列表，未下载/运行CMake和Ninja；直接编译入口是实际验证路径。
''',
'next-stage-readiness.md': '''# 下一阶段就绪度

Windows host core已编译及离线测试；macOS构建NOT RUN，不能复用PE binary为kext。
IpDiscovery/CodeObj保持无IOKit、无allocation接口；offlinevalidation host层依赖STL/异常，
需要无异常错误返回/allocator或独立纯解析kernel适配后才能进kext。
新增IpEntry64不改变旧条目布局，但parser对象内部大小改变，所有macOS使用者需要重新构建。
上游Makefile可核对的目标是x86_64-apple-macos11.0、C++17、-mkernel/-fapple-kext、
-fno-exceptions/-fno-rtti、-nostdinc/-nostdlib；host的STL/异常无法直接用于此目标。
上游submodule pins：Lilu 0515f40b7f2a096adc85e832a4c6104fbd07f936，
MacKernelSDK 05094e5e88cec7caedbfb35e8449ed0db94bf95b；本轮没有递归获取/运行。
具体Xcode/SDK版本尚未验证，不能由Windows Clang版本推出；需要合法Apple SDK和x86_64内核目标。
没有伪造头文件，也不能将Windows PE程序当Mach-O kext。
代码配置仍参考上游macOS11 API，未证明可跨Sequoia/Tahoe；OpenCore只是未来注入条件，不是本轮产物。
签名/加载与安全策略必须独立决定，本轮不改变系统保护或生成可加载kext。
真实显示：板卡数据/连接器/固件/profile、继承GOP、受控模式及恢复计划，需授权。
提交：VM/BO/fence/IP固件和超时；Vulkan：真topology/ABI/RADV；Metal：完整资源/shader/系统接入。
'''
}
for name, content in docs.items():
    write('docs/'+name,content,preserve=True)

P = R['python']; C = R['cpp_unit']['PASS']; D = R['differential']['PASS']; F = R['fuzz']['cases']
unit_names = re.findall(r'^PASS (.+)$',(ROOT/'reports/m65/cpp-unit.log').read_text(encoding='utf-8'),re.MULTILINE)
unit_rows = '\n'.join('| '+name+' | PASS |' for name in unit_names)
change_rows = '\n'.join('| `'+item['path']+'` | '+item['type']+' |' for item in changes)
T = json.loads((ROOT/'reports/m65/toolchain-provenance.json').read_text(encoding='utf-8'))

build_report = f'''# M6.5 实际构建结果

报告日期：2026-10-14。最终验证时间：{R['completed_at']}。

| 项目 | 结果 |
|---|---|
| 编译器 | Clang23.1.3 / LLVM-MinGW20261006 UCRT x86_64 |
| 发布来源 | [官方release](https://github.com/mstorsjo/llvm-mingw/releases/tag/20261006) |
| 归档SHA256 | `{T['sha256']}` |
| 核验 | 官方GitHub asset digest与本地archive一致；非独立签名 |
| 普通C++ unit/probe | 编译、链接、实际执行PASS |
| ASan/UBSan unit/probe | 编译、链接、实际执行PASS |
| canary | 编译PASS；预期非零退出与相应diagnostic已验证 |
| CMake/Ninja | 未运行，不是本次构建依赖 |
| macOS Kext | NOT RUN，不产生安装包 |

实际命令使用显式clang++路径、C++17、警告视为错误、项目include、纯逻辑源文件。
完整可复现argv：[commands.json](m65/commands.json)；工具记录：[toolchain-provenance.json](m65/toolchain-provenance.json)。
Python/Clang启动后会正常读取Windows运行库，未写系统编译器目录或修改PATH。
早期ASan DLL依赖遗漏、盘符log_path和UTF-8问题已修复；历史尝试保留在m65/attempts。
'''
write('reports/m65-build-results.md',build_report)

test_report = f'''# M6.5 实际测试结果

最终记录：[results.json](m65/results.json)，时间{R['completed_at']}。

| 类别 | 真正执行结果 | 说明 |
|---|---|---|
| 原Python基线 | {P['baseline_pass']} PASS / {P['baseline_skip']} SKIP / 0 FAIL | 58项，其中4个PASS为静态检查 |
| 新Python回归 | {P['additional_tests']} PASS / 0 FAIL | metadata/descriptor/组件/范围 |
| Python函数行为合计 | {P['baseline_detail']['behavior_PASS']+P['additional_detail']['behavior_PASS']} PASS | 不计4个静态检查 |
| C++单元 | {C} PASS / 0 FAIL | 真正编译的函数行为 |
| 共享差分 | {D}输入零差异 | 接受/输出/拒绝原因 |
| 受控变异 | {F}输入零差异/无崩溃 | seed759065，非coverage-guided |
| ASan/UBSan | {C}unit + {D+F}输入PASS | 与普通输入重跑，不能累计为独立功能数量 |
| 检测器canary | 2种预期故障被捕获 | 非零退出是预期 |
| 静态分析 | 3个source零warning | 不是函数行为测试 |
| 真Navi44/真shader | SKIP | fixture缺失/无AMDGPU backend |
| GPU/Kext | NOT RUN | 未授权/无macOS构建 |

不把静态检查、重复sanitizer运行或多个截断点混成“驱动功能PASS总数”。
LeakSanitizer没有验证，detect_leaks=0；有限输入没有证明全覆盖。

## C++行为测试清单

| 测试 | 结果 |
|---|---|
{unit_rows}
'''
write('reports/m65-test-results.md',test_report)

security_report = '''# M6.5 安全审查

项目内写入与CPU-only执行获授权；没有GPU实验授权。

| 行为 | 记录 |
|---|---|
| Windows系统/注册表/服务/AMD驱动修改 | 未执行 |
| EFI/BCD/BIOS/SecureBoot/TPM/BitLocker修改 | 未执行 |
| 磁盘分区/第二SSD Linux读取或修改 | 未执行 |
| GPU BAR/MMIO/VBIOS/ROM/DMA/固件访问 | 未执行 |
| Vulkan/DX/OpenCL GPU提交 | 未执行 |
| Kext/SYS/服务加载 | 未执行 |
| 管理员权限请求/全局PATH修改/系统安装 | 未执行 |
| 项目外显式用户文件写入 | 未执行；系统正常缓存/日志不能承诺零写 |
| Git push/远程PR/Release | 未执行 |
| 便携工具 | 官方archive SHA核验后仅项目内解压 |
| host link | 仅parser/validation/tests，不链接device/plugin/IOKit/GPU API |

init恒false、7590不绑定、Makefile禁用。没有部署产物。
统计与源码hash关联；历史M6报告/patch hash保持；当前PASS不是完整OS安全审计。
完整参考树仍有硬件代码/脚本，未执行。工具链下载digest依赖官方托管metadata，不是独立签名或供应链无风险证明。
canary为自有CPU进程故意heap越界/有符号溢出，不影响GPU；仅验证检测器。
测试timeout/输入规模有限，没有额外建立OS内存Job硬配额或lab专属沙箱。
'''
write('reports/m65-security-review.md',security_report)

blockers = '''# M6.5 剩余阻碍与下一阶段

1. 无合法macOS SDK/Xcode构建结果；Kext/内核ABI NOT RUN。
2. host严格校验层依赖STL/异常，不是freestanding kernel-ready。
3. 真Navi44 Discovery/VBIOS/revision/topology/EDID/BAR缺失，未读取硬件。
4. 真gfx1200 ELF缺失：便携Clang无AMDGPU backend，SKIP；不下载不可信SDK。
5. Firmware仅common v1.0、非零CRC拒绝；PSP package/组件身份/签名/实际加载清单未验证。
6. ELF只支持限定MsgPack/metadata和选定kernel一致性，不支持完整relocation/ISA/AMDHSA语义。
7. C++状态机只验证顺序/终止，不自动验证数据；未实现设备生命周期。
8. N44I非生产N48N transport；未知topology/capabilities仍不发布。
9. Fuzz非coverage-guided，有限输入/种子；LeakSanitizer未运行；不证明无漏洞。
10. 真显示、提交、Vulkan、Metal、WindowServer、1440p180Hz全部NOT RUN。

可继续的离线方向：无异常kernel解析层、扩展shared corpus/coverage fuzz、firmware格式与metadata支持、生产ABI。
macOS编译需合法工具链和依赖；加载、实机数据采集、显示/队列实验必须另行授权。
'''
write('reports/m65-remaining-blockers.md',blockers)

full = f'''# M6.5 完整开发报告：RX 9060 XT / Navi 44 原型工程化与 C++ 离线验证

> 交付日期：2026-10-14，Asia/Shanghai。
>
> 最终测试记录：{R['completed_at']}。
>
> 项目：`D:\\CodexWorkSpace\\黑苹果研究\\Hackintosh-Navi44-Lab`。
>
> **实际完成 Windows C++ 编译、函数测试、Python/C++ 差分、受控变异及 ASan/UBSan。未构建或加载 macOS kext，未操作真实 RX9060XT。**

## 目录

1. [本轮真实成果](#1-本轮真实成果)
2. [编译环境与来源](#2-编译环境与来源)
3. [实际构建和代码架构](#3-实际构建和代码架构)
4. [跨语言一致性与修复](#4-跨语言一致性与修复)
5. [测试与可复现证据](#5-测试与可复现证据)
6. [安全审查与限制](#6-安全审查与限制)
7. [成熟度与验收](#7-成熟度与验收)
8. [下一阶段与交付索引](#8-下一阶段与交付索引)

## 1. 本轮真实成果

### 1.1 从 M6 到 M6.5 的变化

上一阶段记录为58项Python测试，56 PASS、2 SKIP；C++、kext、GPU均NOT RUN。
本轮先保存源码/报告快照并复现原基线，再获取便携工具链真正编译原C++测试。
后续实现64位Discovery和严格校验层，增加共享输入与sanitizer，而不是把原研究重述为新开发。

| 模块 | 本轮实际新增/修改 |
|---|---|
| C++工具链 | 官方LLVM-MinGW portable；完整Clang/LLD/C++runtime |
| Discovery | 新64位entry/query/byte-offset；精确binary入口；旧接口防截断 |
| Firmware | 编译可用的common header检查和C++需求模型；明确组件/CRC边界 |
| ELF/metadata | C++严格host解析，与Python一致；descriptor/符号/kernarg对照 |
| 状态/ABI | C++离线顺序约束、失败终止、N44I验证 |
| 质量体系 | 实际C++函数单元、shared corpus、差分、变异、ASan/UBSan及canary |
| 自动化 | run_all_offline_tests.py：完整项目内统一入口、真实日志统计、源码hash |
| 交付 | 当前报告、分项文档、独立patch和机器可读记录 |

### 1.2 项目目标与范围

固定硬件为i5-12600KF（无核显）、B760M、RX9060XT/1002:7590；没有建议更换硬件。
唯一已确认显示GPU保持Windows原驱动；Intel256GB第二盘已有EFI/Linux，本轮不读取或修改。
允许项目内源码、便携工具、CPU-only用户态测试；不允许系统/驱动/启动/分区/真实GPU操作。
最终成果是工程化的离线软件原型，不能等同可日常使用macOS。

### 1.3 保留历史

M6快照在`reports/m65/history`。原`reports/test-results.json`、`reports/test-log.txt`、
`patches/navi44-offline-prototype.patch`与快照SHA一致，没有改写成M6.5结果。
本轮日志、命令和失败尝试使用`reports/m65`及`attempts`；新增文档与独立patch。
这是基线快照、差异补丁和日志追踪，不声称每一次中间编辑都形成Git提交。

## 2. 编译环境与来源

### 2.1 实际工具

| 项目 | 实际值 |
|---|---|
| 平台 | Windows，x86_64-w64-windows-gnu CPU-only用户态 |
| 编译器 | Clang23.1.3，版本输出见compiler-version.log |
| 便携发行 | LLVM-MinGW 20261006 UCRT x86_64 |
| 完整包 | Clang、LLD、mingw-w64头/import库、libc++/libunwind/compiler-rt |
| Python | 现有3.12.13；未安装依赖 |
| CMake/Ninja | 未获取或运行；实际采用显式clang++命令 |
| Apple SDK/Xcode | 未获取；macOS构建NOT RUN |

### 2.2 来源与完整性

[LLVM-MinGW官方发布](https://github.com/mstorsjo/llvm-mingw/releases/tag/20261006)。
资产：`llvm-mingw-20261006-ucrt-x86_64.zip`，190,836,485 bytes。

```text
SHA-256: {T['sha256']}
```

下载后的archive与官方GitHub资产digest一致，之后才解压。此为同一官方托管渠道的完整性核验，
不是独立签名认证。没有执行系统安装器、安装Windows SDK/VS、注册服务、改PATH或请求管理员权限。
工具链各许可证保留在项目发行包；新代码沿用上游BSD-3-Clause。

### 2.3 版本固定

| 上游 | 固定参考 |
|---|---|
| AMDRadeonRDNA4 | 49f7f20c00dd154384418078f8a09e79c400a06a |
| Cobalt64 | d6c9aedf8e6526a39e349b5886cbc8c7ddf77f65 |
| Cobalt PR12 | 2c3bba7771ed0d51dc01a6882987a4cfbbd1afe2，先前查询未合并/未应用 |
| Linux Discovery | 24a19b953e2a3d0ea5a8c4951a0ab8f32720c907 |
| LLVM ELF定义 | llvmorg-20.1.8 / 87f0227cb60147a26a1eeb4fb06e3b505e9c7261 |
| Mesa补丁参考 | f5cb8ee032adabef599ae892ec4e42d796b84da9 |

收尾阶段没有重新查询最新上游，以上为实际固定来源，不能当2026-10-14的实时维护状态声明。

## 3. 实际构建和代码架构

### 3.1 实际命令

统一入口：

```powershell
& 'D:\\RuntimeEnvironment\\mise\\mise\\data\\installs\\python\\3.12.13\\python.exe' -I -B -X utf8 run_all_offline_tests.py
```

普通C++编译使用的等效参数（完整绝对路径argv保存在commands.json）：

```text
clang++ -std=c++17 -Wall -Wextra -Werror -static -g -O1
  -I development/AMDRadeonRDNA4-Navi44/src
  tests/unit/m65_unit.cpp
  development/AMDRadeonRDNA4-Navi44/src/ipdiscovery.cpp
  development/AMDRadeonRDNA4-Navi44/src/offlinevalidation.cpp
  development/AMDRadeonRDNA4-Navi44/src/codeobj.cpp
  -o build/m65/unit.exe
```

sanitized target再加`-fsanitize=address,undefined -fno-omit-frame-pointer`。
普通/sanitized unit与probe均真实编译、链接、执行，最终无普通构建错误。
canary另分别使用address与undefined，非零退出为预期错误被捕获。
没有伪造Apple头文件，没有生成kext安装包。

### 3.2 分层与未来内核边界

```text
ASIC / IpDiscovery / CodeObj（无IOKit，部分allocation-free）
                 ↓
Offline host validation（STL、异常、metadata）
                 ↓
C++ unit/probe ↔ Python独立实现
                 ↓
共享输入 / 差分 / 有界变异 / ASan-UBSan

IOKit/PCI/MMIO/firmware upload/queue/display adapters：future
```

Windows编译通过不代表内核兼容。严格host层使用STL和异常，未来需要freestanding适配/allocator/
无异常错误返回；新增parser对象内部字段改变大小，macOS相关使用者需重编译。旧IpEntry布局未改变。
上游可查目标为x86_64-apple-macos11.0、C++17、-mkernel/-fapple-kext、-fno-exceptions/-fno-rtti。
固定Lilu pin为0515f40b7f2a096adc85e832a4c6104fbd07f936，MacKernelSDK为
05094e5e88cec7caedbfb35e8449ed0db94bf95b。具体Xcode/Apple SDK未验证，不从host版本虚构兼容结论。

### 3.3 64位Discovery

新增`IpEntry64`、`initBinary`、`ipAt64`、`findIp64`、`regByteOffset64`。
legacy `init`保留内存中的ROM扫描；差分使用从offset0开始的精确binary入口。
64位base不截断；旧32位查询只在值可表示时成功。高位、加法、乘4越界均拒绝。
base是寄存器segment dword基址，不等于物理BAR地址，本轮没有改变任何寄存器访问逻辑。
buffer为caller-owned不可变view；调用者必须维护有效期。多die/未知版本仍fail-closed。

### 3.4 Firmware/ELF/状态

Firmware检查common header v1.0的长度、payload和IP major/minor；C++已有需求清单模型。
组件标识是调用方声明与允许名称检查，不是common header内不存在的组件ID认证。
CRC非零明确未验证，不猜算法或加载成功；PSP签名/package和真实版本仍缺。

ELF严格层检查完整文件范围→metadata→选定kernel的symbol/descriptor；对kernarg/group/private大小对照。
固定常量gfx1200=0x048、gfx1201=0x04e；不通过重新标记ELF使它“兼容”。
metadata仅限定MsgPack与AMDHSA版本子集，不证明ISA正确。旧loader并未自动改成完整strict API。

C++状态机验证顺序和终止，不自动验证数据或真实设备；OfflineReady绝不授权硬件初始化。
N44I仍为32字节模拟协议，capabilities/reserved为0，非N48N transport，未知topology不公开。

## 4. 跨语言一致性与修复

### 4.1 独立比较方法

Python函数和真实编译的C++probe读相同bytes，输出canonical结果。比较接受/拒绝、版本、IP、地址、
GC_INFO；并测试profile、firmware需求/结构、ELF/descriptor、ABI与错误原因。
两端不通过共享执行结果“互相证明”。共同支持输入最终{D}项零差异。
多数共享case是合成数据的截断/错误变体，不是{D}份真实硬件样本。

### 4.2 实际发现与修复

| 问题 | 定位与修复 | 证据 |
|---|---|---|
| Windows默认GBK读取Clang中文路径 | subprocess显式UTF-8 | 入口最终完整成功，旧尝试保留 |
| ASan startup缺DLL | ASan依赖libc++，后者依赖libunwind；仅复制到build | sanitized执行和canary |
| ASAN_OPTIONS盘符冒号 | 使用项目相对log_path | 选项解析错误消失 |
| Python bytearray symbol不可hash | 转bytes作为符号键 | 新kernel测试通过 |
| C++ descriptor entry有符号偏移 | 显式加法上溢/下溢拒绝，NOBITS不当代码 | 回归与sanitizer |
| 完整section与metadata检查顺序不同 | 两端先检查完整文件envelope再语义 | 差分零差异 |
| metadata/descriptor内容不一致 | 新strict接口比较symbol/kernarg/group/private | 合成kernel正常/损坏测试 |
| 固定统计数可能误报 | 从unittest日志计算、源码hash关联 | 最终results.json |

保存合成回归样本`tests/fixtures/m65-invalid-strtab.bin`；其生成规则来自synthetic kernel并将字符串表size高位
改成越界，不能称为RX9060XT捕获。部分中间差异是错误分类顺序不同，两端原本都拒绝，未误称已发现硬件漏洞。

## 5. 测试与可复现证据

### 5.1 分类型结果

| 类别 | 最终结果 | 限定 |
|---|---|---|
| Python原基线 | 58总计：56 PASS、2 SKIP、0 FAIL | 4个PASS是静态检查 |
| Python新增 | {P['additional_tests']} PASS | 真正函数回归 |
| Python函数行为 | {P['baseline_detail']['behavior_PASS']+P['additional_detail']['behavior_PASS']} PASS | 不含4个静态检查 |
| C++行为单元 | {C} PASS、0 FAIL | 真实Windows二进制 |
| shared差分 | {D}输入、0差异 | 接受/语义/错误原因 |
| deterministic mutation | {F}输入、0差异/崩溃 | seed759065，非coverage-guided |
| ASan/UBSan重跑 | {C}unit + {D+F}输入通过 | 重复覆盖，不额外累计功能PASS |
| detector canary | heap越界、signed overflow均被捕获 | 预期CPU进程失败 |
| Clang static analyzer | 3个source、零warning | 不是实机/动态证明 |

原真实Discovery和真实shader测试仍SKIP。Clang的registered targets没有AMDGPU，
不生成伪造真实编译产物。macOS/kext/GPU/显示/提交/Vulkan/Metal/WindowServer/180Hz全部NOT RUN。

### 5.2 有界执行

单顺序probe，输入由当前约1200 bytes的种子产生；固定2400次，测试进程timeout30秒、编译60秒。
没有无限fuzz或GPU压力测试；未建立额外OS Job内存硬配额。ASan检测通过仅针对当前工作负载；
LeakSanitizer没有运行，detect_leaks=0。零warning/零差异不是全代码无漏洞或规范完整证明。

### 5.3 证据位置

- [结果JSON](m65/results.json)：来源hash、时间与分类统计。
- [完整命令](m65/commands.json)：实际argv、退出码、耗时与expected_failure。
- [C++单元日志](m65/cpp-unit.log)、[Python新增](m65/python-m65-tests.log)。
- [共享输入](m65/shared-corpus.json)、[差分](m65/differential-differences.json)、[变异](m65/fuzz-seed-759065-differences.json)。
- [Sanitizer日志](m65/sanitized-unit.log)、[对应差分](m65/sanitized-corpus-differences.json)。
- [来源记录](m65/toolchain-provenance.json)、[历史完整性](m65/history-integrity.json)。
- detector详细diagnostic在`m65/asan-canary.*`/`ubsan-canary.*`及canary日志。

## 6. 安全审查与限制

### 6.1 禁止操作的实际记录

Windows系统/注册表/服务/驱动、EFI/BCD/BIOS、安全策略、硬盘分区、第二盘Linux、
GPU BAR/MMIO/VBIOS/ROM/DMA/固件、Vulkan/DX/OpenCL提交、Kext加载、管理员权限、
global PATH、远程发布：**未执行**。
主动源码、工具、runtime、日志和报告输出仅在lab；系统运行库正常读取与OS缓存日志不能承诺零副作用。
没有进行系统级文件写入追踪审计，不能提供绝对安全证明。

### 6.2 门禁仍保留

7590不绑定；hardwareInitializationAllowed恒false，无普通参数能解除；开发Makefile禁用。
host source清单没有device.cpp/plugin.cpp/IOKit/GPU API，不生成驱动安装器。
该分支也不能当作Navi48正常部署分支，因为所有设备init默认拒绝。
源码门禁不替代OS沙箱，完整参考树含未运行的危险脚本。

### 6.3 技术和维护边界

Firmware仅有限结构，metadata仅子集，未处理完整relocation/ISA；有限fuzz覆盖。
生产ABI和单一GPU所有者尚未接入；真实revision/active topology/BAR/固件缺失。
WindowsSTL/异常host层与Darwin内核仍需适配；不伪造Apple头文件或绕过签名/保护。
新增源码保留BSD；LLVM/MinGW/引用各保留许可证，开源驱动并不授予非Apple硬件macOS许可。

## 7. 成熟度与验收

| 项目 | 判断 |
|---|---|
| ASIC Profile | 离线识别/target/revision状态通过；未知能力仍关闭 |
| Discovery | C++32/64及legacy窄化已编译测试；真fixture缺失 |
| Firmware | CPU结构/需求模型可用；真实组件/CRC/签名未验证 |
| ELF | strict envelope/metadata/descriptor已跨语言测试；真ISA产物缺失 |
| C++构建 | Windows host完成；非macOS/kext |
| 自动化 | 统一入口、分类统计、日志/history/hash完成 |
| macOS准备 | 依赖/架构差距明确，SDK/ABI未编译 |
| 显示准备 | 基础软件证据提高；真实显示未验证 |
| Vulkan/Metal准备 | 数据接口规划与底层参考；无加速成果 |

M6.5核心验收：原基线复现、便携工具核验、实际编译运行、Navi44/Navi48与target区分、
shared格式一致、默认门禁及真实证据均完成。尽可能项目中的64位、firmware/ELF强化、sanitizer、
变异测试已完成有限实现；真正macOS/GPU不属于本轮验收。

## 8. 下一阶段与交付索引

### 8.1 距离A—E的具体缺口

| 目标 | 仍需工作 |
|---|---|
| A. macOS kext编译 | 合法Xcode/SDK、固定Lilu/MacKernelSDK、内核ABI/C++选项、无异常/allocator适配 |
| B. RX9060XT基础显示 | 真profile/IP/连接器/BAR/固件/EDID；继承GOP；有界模式与恢复；实机授权 |
| C. 命令提交 | VM/BO、PSP/SMU/SDMA/MES/CP、fence、中断、timeout、DMA安全与隔离 |
| D. Vulkan | 真实topology/GB_ADDR_CONFIG/VRAM/BAR、版本化生产ABI、Darwin RADV与验证 |
| E. Metal | 完整资源/共享纹理/argument buffers、shader转译/cache、私有ABI、WindowServer及长期测试 |

优先继续无异常kernel-friendly纯逻辑、更多合法fixtures、coverage fuzz与生产ABI审查，
不应把当前PASS用于自动加载或安装。实机、驱动签名/加载条件和安全保护变化需独立决定。

### 8.2 修改清单

相对项目根目录，与M6快照比较；历史记录、工具二进制和生成日志不混入源码patch。

| 路径 | 类型 |
|---|---|
{change_rows}

### 8.3 交付链接

- [编译报告](m65-build-results.md)、[测试报告](m65-test-results.md)。
- [安全审查](m65-security-review.md)、[未完成项](m65-remaining-blockers.md)。
- [跨语言设计](../docs/cross-language-parser.md)、[host构建](../docs/cpp-host-build.md)、[下阶段条件](../docs/next-stage-readiness.md)。
- [M6→M6.5 patch](../patches/m65-from-m6-offline.patch)。
- [上游累计patch](../patches/navi44-m65-offline-cumulative.patch)。
- [机器可读修改清单](m65/changed-files.json)。

patch不包含便携工具、真实固件或二进制fixture；合成fixture可由包含的源码重新生成。
它们仍是离线适配patch，不能安装到OpenCore或当作成熟驱动。

### 8.4 最终交付核对

已核对测试记录中的源码SHA、交付文件SHA、本地文档链接、原M6历史文件校验值及上游快照。
累计patch对固定上游、增量patch对独立M6基线副本均通过`git apply --check`，没有实际应用。
机器可读证明见[delivery-verification.json](m65/delivery-verification.json)。
该核对只证明当前交付对应关系与patch可应用性，不证明驱动硬件兼容或系统绝对安全。

---

**最终结论：M6.5完成真实Windows C++离线工程化验证及交付；当前进展是软件原型成熟度提升，
不是RX9060XT硬件显示或Metal兼容性证明。完成后停止，不进入macOS安装、kext部署或GPU实验。**
'''
write('reports/m65-development-report.md',full)

artifacts = ['reports/m65-development-report.md','reports/m65-build-results.md','reports/m65-test-results.md',
    'reports/m65-security-review.md','reports/m65-remaining-blockers.md','reports/m65/results.json',
    'reports/m65/commands.json','patches/m65-from-m6-offline.patch','patches/navi44-m65-offline-cumulative.patch']
write('reports/m65/deliverable-sha256.json',json.dumps({p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in artifacts},indent=2))
print(json.dumps({'report':'reports/m65-development-report.md','source_changes':len(changes),
                  'M6_history_preserved':all(historical_checks.values()),'status':'documentation generated'},ensure_ascii=False))
