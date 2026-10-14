# M6.5 完整开发报告：RX 9060 XT / Navi 44 原型工程化与 C++ 离线验证

> 交付日期：2026-10-14，Asia/Shanghai。
>
> 最终测试记录：2026-10-14T00:37:40.503321+08:00。
>
> 项目：`D:\CodexWorkSpace\黑苹果研究\Hackintosh-Navi44-Lab`。
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
SHA-256: 317492c456aa27ee607a5919f1d2d38dcdc1112516a24d0bf4b00d078f52d17a
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
& 'D:\RuntimeEnvironment\mise\mise\data\installs\python\3.12.13\python.exe' -I -B -X utf8 run_all_offline_tests.py
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
两端不通过共享执行结果“互相证明”。共同支持输入最终537项零差异。
多数共享case是合成数据的截断/错误变体，不是537份真实硬件样本。

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
| Python新增 | 11 PASS | 真正函数回归 |
| Python函数行为 | 63 PASS | 不含4个静态检查 |
| C++行为单元 | 34 PASS、0 FAIL | 真实Windows二进制 |
| shared差分 | 537输入、0差异 | 接受/语义/错误原因 |
| deterministic mutation | 2400输入、0差异/崩溃 | seed759065，非coverage-guided |
| ASan/UBSan重跑 | 34unit + 2937输入通过 | 重复覆盖，不额外累计功能PASS |
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
| `CMakeLists.txt` | modified |
| `run_all_offline_tests.py` | added |
| `finalize_m65.py` | added |
| `validate_m65_delivery.py` | added |
| `m65_prepare.py` | added |
| `m65_acquire_toolchain.py` | added |
| `m65_replace_discovery.py` | added |
| `tests/test_m65.py` | added |
| `tests/fixtures/synthetic.py` | modified |
| `tests/unit/m65_unit.cpp` | added |
| `tests/unit/m65_probe.cpp` | added |
| `tests/unit/sanitizer_canary.cpp` | added |
| `tests/unit/sanitizer_smoke.cpp` | added |
| `development/AMDRadeonRDNA4-Navi44/src/codeobj.cpp` | modified |
| `development/AMDRadeonRDNA4-Navi44/src/ipdiscovery.hpp` | modified |
| `development/AMDRadeonRDNA4-Navi44/src/ipdiscovery.cpp` | modified |
| `development/AMDRadeonRDNA4-Navi44/src/offlinevalidation.hpp` | added |
| `development/AMDRadeonRDNA4-Navi44/src/offlinevalidation.cpp` | added |
| `development/AMDRadeonRDNA4-Navi44/host/navi44.py` | modified |

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
