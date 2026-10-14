# RX 9060 XT / Navi 44 原生 macOS 驱动适配原型：本轮完整开发报告

> 报告日期：2026 年 10 月 13 日，Asia/Shanghai。
>
> 项目：Hackintosh-Navi44-Lab。
>
> 阶段：实际源码开发、CPU-only 离线校验、补丁和文档交付。
>
> **结论：已创建真实项目代码并执行离线测试。最终记录为 58 项测试：56 PASS、0 FAIL、2 SKIP。C++ 编译、macOS kext 构建和全部真实 GPU 功能为 NOT RUN。**
>
> 本报告汇总上一开发轮次已有源码、日志和来源记录。生成本报告没有重新执行测试，没有新增驱动功能，也没有进入部署或硬件实验阶段。

## 目录

1. [开发进度总结](#progress)
2. [开发环境与源码来源](#environment)
3. [修改文件与交付物](#files)
4. [Navi 44 原型具体实现](#implementation)
5. [实际离线测试结果](#tests)
6. [代码质量、安全边界与风险](#quality)
7. [当前功能等级与验收判断](#acceptance)
8. [下一阶段与剩余阻碍](#next)
9. [附录：测试清单、来源和校验信息](#appendix)

<a id="progress"></a>

## 1. 开发进度总结

### 1.1 实际完成的工作

本轮已从研究进入实际编码，在新建独立项目内完成以下产物：

1. 克隆并固定 AMDRadeonRDNA4 和 Cobalt64 公开源码。
2. 建立 AMDRadeonRDNA4 独立开发副本，保留上游参考快照。
3. 实现 C++ ASIC Profile，区分 Navi 44、Navi 48、gfx1200、gfx1201、PCI ID 与 revision 状态。
4. 修改上游 C++ code object 校验，使目标从固定 gfx1201 变为显式参数，并保留旧调用默认目标。
5. 加固上游 C++ Discovery 解析器的边界、checksum、重复 IP、状态清理和地址溢出检查。
6. 实现独立 Python host library，包括完整保留 64 位地址的 Discovery 解析、固件需求模型、ELF/metadata 校验和离线状态机。
7. 实现纯数据的版本化设备信息协议原型。
8. 加入默认禁止设备初始化、拒绝 Navi 44 硬件绑定、禁用上游构建目标等门禁。
9. 编写并实际运行 CPU-only Python 测试，提供 C++ host 测试源码与独立 CMake 配置。
10. 生成补丁、机器可读结果、日志、来源记录、架构文档和阻碍报告。

这不是伪代码报告：上述源码、测试和补丁真实存在于工作区。与此同时，它还不是经过编译及硬件验证的 macOS 驱动。

### 1.2 本轮范围与授权

允许在独立开发目录内创建/编辑文件、获取公开源码、运行安全的无特权 CPU-only 测试。未授权驱动部署、系统配置修改或真实 GPU 访问。

实际未执行：

- Windows 注册表、服务、驱动、PATH 或全局 Git 配置修改。
- EFI、BCD、BIOS、UEFI、TPM、Secure Boot、BitLocker 修改。
- 硬盘分区、格式化、初始化或安装 macOS。
- kext/SYS 加载、GPU MMIO、PCI BAR、DMA、I/O 端口访问。
- GPU 固件上传、刷写、命令提交、压力测试或显示设置改变。
- 安装 SDK、编译器、WSL、虚拟机、系统服务或管理员组件。
- 向 GitHub 推送、创建远程分支、PR 或 Release。

### 1.3 M0—M6 实际进度

| 里程碑 | 本轮完成内容 | 完成边界 |
|---|---|---|
| M0 环境与源码 | 独立目录、源码固定、工具检查、许可证与来源记录 | 没有完整编译环境；没有递归获取 SDK/submodule |
| M1 Profile | 设备、ASIC、target、revision、未知能力描述 | 没有真实 revision allowlist 和活跃拓扑 |
| M2 Discovery/Firmware | Python parser/manifest；C++ parser 加固 | 真实 fixture、固件及多格式仍缺 |
| M3 Shader target | C++ expected target 参数化；Python ELF/metadata 校验 | 没有真正 gfx1200 编译产物 |
| M4 门禁与集成 | 修改 match/init/build；CPU-only 构建配置和实际 Python 测试 | C++ 和 kext 没有编译 |
| M5 Cobalt 接口 | N44I 模拟数据协议及接入文档 | 不兼容生产 N48N；没有 IOUserClient 或 RADV 连接 |
| M6 质量交付 | 测试日志、补丁、报告、hash、补丁可应用性检查 | 不是完整安全审计或实机验收 |

<a id="environment"></a>

## 2. 开发环境与源码来源

### 2.1 独立目录

```text
D:\CodexWorkSpace\黑苹果研究\Hackintosh-Navi44-Lab
```

创建前确认该目录不存在，没有覆盖原研究报告或已有项目。所有主动生成的源码、构建配置、补丁、报告及临时目录均限制在此项目内。

```text
Hackintosh-Navi44-Lab/
├── upstream/
│   ├── AMDRadeonRDNA4/
│   ├── Cobalt64/
│   └── references/
│       ├── linux-discovery.h
│       └── llvm-ELF.h
├── development/
│   └── AMDRadeonRDNA4-Navi44/
│       ├── src/
│       └── host/navi44.py
├── tests/
│   ├── fixtures/synthetic.py
│   ├── unit/host_tests.cpp
│   └── test_offline.py
├── build/
├── tmp/
├── docs/
├── patches/navi44-offline-prototype.patch
├── reports/
├── CMakeLists.txt
├── build_offline.ps1
├── run_offline.py
├── tools_integrate.py
├── finish_reports.py
└── README.md
```

`build/` 是未来 CPU-only 构建产物的预留位置，不表示已经生成 C++ 可执行程序。

### 2.2 工具情况

| 工具 | 本轮实际情况 |
|---|---|
| PowerShell | 用于目录内文件和现有工具调用 |
| Git | 2.55.0.windows.4 |
| Python | 3.12.13，现有实际 executable |
| Python 路径 | `D:\RuntimeEnvironment\mise\mise\data\installs\python\3.12.13\python.exe` |
| C++ compiler | 未在已检查路径中找到可用 MSVC/Clang/GCC |
| CMake | 未找到可用工具 |
| macOS SDK/Xcode | 没有可用环境 |
| 第三方 Python 依赖 | 不需要，没有安装 |

Python 版本字符串中的 `MSC` 说明 Python 自身使用的构建工具，并不证明本机存在可调用 MSVC 编译器。

### 2.3 固定源码与公开状态

| 来源 | 固定版本 | 本轮处理 |
|---|---|---|
| AMDRadeonRDNA4 | `49f7f20c00dd154384418078f8a09e79c400a06a` | 克隆、检出、复制开发副本 |
| Cobalt64 | `d6c9aedf8e6526a39e349b5886cbc8c7ddf77f65` | 克隆参考，不应用其 GPU 驱动 |
| Cobalt PR #12 | `2c3bba7771ed0d51dc01a6882987a4cfbbd1afe2` | 复查为 open/unmerged，没有应用 |
| LLVM | tag `llvmorg-20.1.8`；commit `87f0227cb60147a26a1eeb4fb06e3b505e9c7261` | 仅下载固定 ELF 文本头文件 |
| Linux | `24a19b953e2a3d0ea5a8c4951a0ab8f32720c907` | 仅下载固定 Discovery 文本头文件 |
| Mesa | Cobalt 补丁基础 `f5cb8ee032adabef599ae892ec4e42d796b84da9` | 参考已有补丁，没有下载完整 Mesa |

源码获取时复查：AMDRadeonRDNA4 和 Cobalt64 主线与上述前期固定版本相同。因此本轮没有依据新的主线变更宣称已有 Navi 44 成品支持。该状态是本轮查询结果，不保证以后保持不变。

### 2.4 获取过程与隔离措施

最初 sandbox 网络请求因 TLS credential 不可用失败；在具体联网源码获取请求获得允许后完成克隆和文本下载。没有请求管理员权限。

Git 使用 `--no-checkout` 获取后检出固定 commit，不执行仓库 hooks 或构建脚本，不递归初始化 submodule。使用进程/命令级配置禁用 hooks、自动维护及 GC，并且没有写全局 Git 配置。

不同执行用户引发 Git 所有权检查时，只对已知克隆目录使用单条命令的 `safe.directory` 参数；没有执行 Git 建议的全局配置修改。

TMP/TEMP 显式指向 `lab/tmp`；Python 使用 `-I -B` 隔离用户环境、禁止 pyc 写入。普通操作系统和网络缓存不被描述为物理零写入。

### 2.5 本机硬件定位

目标仍为用户提供的 i5-12600KF、MS-Terminator B760M D5、RX 9060 XT/1002:7590、32GB DDR5、Windows 11 IoT Enterprise LTSC。

12600KF 没有核显，RX 9060 XT 是唯一已确认显示适配器。WD SN850X 原 Windows 保持不变；Intel 256GB 第二盘已有 EFI/Linux 分区，本轮未触碰。

本轮没有通过 GPU 寄存器、ROM BAR 或 VBIOS 读取重新检测硬件，没有获取序列号、账户凭据或密钥。

<a id="files"></a>

## 3. 修改文件与交付物

### 3.1 开发副本差异

以下路径相对于 `development/AMDRadeonRDNA4-Navi44/`。上游参考快照未应用这些修改。

| 文件 | 类型 | 具体作用 |
|---|---|---|
| `Makefile` | 修改 | 明确报错，禁用上游 kext/硬件工具构建目标 |
| `src/asicprofile.hpp` | 新增 | ASIC、target、revision、预期 GC、未知拓扑和恒 false 授权 |
| `src/offlinefirmware.hpp` | 新增 | 纯 CPU common firmware header 结构检查 |
| `src/plugin.cpp` | 修改 | 复用 ASIC 识别；Navi 44 明确返回不绑定 |
| `src/device.cpp` | 修改 | 初始化入口在接触设备状态前检查恒 false 门禁 |
| `src/codeobj.hpp` | 修改 | 新增 Expected Target 参数，默认 Gfx1201 |
| `src/codeobj.cpp` | 修改 | 目标匹配、Unknown 拒绝、空 kernel name 拒绝及地址范围加固 |
| `src/ipdiscovery.hpp` | 修改 | 记录 binary/table 的边界 |
| `src/ipdiscovery.cpp` | 修改 | 版本、表范围/checksum、重复、溢出及失败状态加固 |
| `host/navi44.py` | 新增 | 可在 Windows 用户态执行的完整离线参考实现 |

### 3.2 测试和工具

| 文件 | 用途 |
|---|---|
| `tests/test_offline.py` | 58 项 Python 逻辑/静态检查与 SKIP 定义 |
| `tests/fixtures/synthetic.py` | 合成 Discovery、ELF、metadata 和固件头数据 |
| `tests/unit/host_tests.cpp` | C++ 纯逻辑测试源码，尚未编译/运行 |
| `CMakeLists.txt` | 只列纯解析代码的 CPU-only C++ target |
| `run_offline.py` | 执行测试，生成 JSON 和日志 |
| `build_offline.ps1` | 用已有 Python 执行，临时设置项目内 TMP/TEMP 后恢复 |
| `tools_integrate.py` | 本轮一次性、已审查的本地源码转换记录 |
| `finish_reports.py` | 生成补丁、来源记录和分项文档，不访问网络 |

`tools_integrate.py` 不需要再次运行，不是安装器，也不是幂等的日常构建入口。

### 3.3 文档、补丁与结果

架构资料：

- [architecture.md](../docs/architecture.md)
- [navi44-profile.md](../docs/navi44-profile.md)
- [firmware-and-discovery.md](../docs/firmware-and-discovery.md)
- [gfx1200-target.md](../docs/gfx1200-target.md)
- [safety-boundaries.md](../docs/safety-boundaries.md)
- [cobalt-integration-plan.md](../docs/cobalt-integration-plan.md)

主要产物：

- [源码补丁](../patches/navi44-offline-prototype.patch)
- [测试结果 JSON](test-results.json)
- [测试完整日志](test-log.txt)
- [来源记录](provenance.json)
- [修改清单](changed-files.json)
- [关键产物 SHA-256](artifact-sha256.json)
- [安全记录](safety-audit.md)
- [剩余阻碍](remaining-blockers.md)

补丁已经对固定上游执行 `git apply --check` 并通过；没有实际应用到上游参考树，也没有推送远程。

<a id="implementation"></a>

## 4. Navi 44 原型具体实现

### 4.1 Profile 与识别

| 输入 | 结果 |
|---|---|
| 1002:7590 | Navi44 / gfx1200 |
| 1002:7550 | Navi48 / gfx1201 |
| 1002:7551 | Navi48 / gfx1201 |
| 其他 vendor/device | Unknown 或明确错误 |

revision 区分“未提供”与明确值，包括 0；Python 检查 0..255。没有真实 revision 验证表，因此 `revisionVerified` 始终 false。

GC 12.0.0/12.0.1 是对应家族的预期描述，不是本机捕获结果。SE/CU/RB/TCC、VRAM 和 BAR 等真实拓扑没有填入 Navi 48 值；C++ 以零加 `verified=false` 表示 Unknown，而不是认定硬件拥有零资源。

capabilities 为空/零，不公开 Metal、显示模式、队列、睡眠等未验证能力。

### 4.2 识别、绑定和初始化的分离

离线 `identify()` 可以识别 7590，但上游 match hook 遇到 Navi44 明确拒绝。这避免将识别能力误当成硬件适配完成。

`RDNA4Device::init()` 的入口增加 `hardwareInitializationAllowed()` 检查，该函数在当前原型恒为 false，没有运行参数能开启。

重要影响：**当前开发副本对所有 ASIC 默认拒绝设备初始化，包括 Navi48。** 保留的是 Navi48 的纯识别、默认 shader target 和已有源代码，不是原 Navi48 的可部署硬件行为。该副本不应被用于既有 Navi48 安装。

完整参考树仍含硬件函数和旧工具。门禁与 CPU-only target 降低误用风险，不代表每个原始硬件函数都被删除，也不替代操作系统权限隔离。

### 4.3 Discovery：Python host parser

输入为调用者已经拥有的内存 bytes，不读取真实 GPU。支持范围：

- Binary v1.0..1.3、v2.0。
- IPDS v3/v4。
- 一个 die；多 die 和其他版本明确拒绝。
- 32 位及 64 位 base address，64 位值不截断。
- GC_INFO 基础 v1.0/v2.0，其他版本拒绝。

检查内容：

1. Magic、版本、声明大小、header/table 数量。
2. binary checksum 和每个有效 table checksum。
3. 表范围、表重叠、die offset/id、IP 数量。
4. base 数量、变长记录范围及地址乘 4 的溢出。
5. 重复 `(hw_id, instance)`。
6. GC_INFO 长度和非零 SE/RB 描述。
7. profile 的 GC 版本匹配。
8. 拓扑缺失时拒绝后续要求验证。

未知 IP 保留在 `unknown_ids`，不自动获得功能支持。GC_INFO 字段是输入描述，不等于活跃 CU mask、真实缓存配置或 BAR 布局已经验证。

### 4.4 Discovery：C++ 上游加固

修改原 `IpDiscovery` 的范围记录、读取边界、版本选择、IPDS checksum、重复 IP、GC_INFO 和寄存器 byte offset 溢出处理；失败初始化清理残留计数/偏移。

**C++ 原公开 `IpEntry` 使用 uint32_t bases，本轮保留接口并明确拒绝 64 位编码。** 完整 64 位解析在 Python 参考实现中完成。不能把两者描述为同样覆盖，也不能声称 Python PASS 验证了 C++。

原 C++ 扫描器还保留既有扫描和最小 buffer 限制；未来需通过 C++ fixture 回归验证真实有效数据没有被过度拒绝。

### 4.5 Firmware Manifest

Python 依据 profile 和输入 Discovery 构造 GC、PSP、SMU、SDMA、DCN/DMUB 等组件需求，要求关键 IP instance 存在，不直接给 Navi44 分配 Navi48 固件。

当前组件清单是研发需求模型，**不是经过实机确认的完整固件加载顺序**。PSP/SMU/SDMA/DCN 的本机版本未知，各子版本组件规则仍需核对。

结构检查仅支持 common firmware header v1.0，检查：

- 声明大小、header 大小、payload offset/size。
- IP major/minor 对应关系。
- 重复或缺失组件。
- 未支持 header 版本明确拒绝。
- 非零 CRC 返回未验证错误，不跳过后伪报成功。

没有 AMD/PSP 签名验证、真实固件下载、上传、签名修改或 PSP 绕过。PSP package v2 等组件格式尚未实现。header 不包含完整 IP revision 的事实不能被 Manifest 的声明替代。

### 4.6 gfx1200 与 ELF

从固定 LLVM ELF.h 重新核对：

```text
EF_AMDGPU_MACH_AMDGCN_GFX1200 = 0x048
EF_AMDGPU_MACH_AMDGCN_GFX1201 = 0x04e
```

C++ `parseImage()`、`findKernel()` 增加明确的 expected target；旧调用默认 gfx1201。Unknown 和交叉目标拒绝，不重标记 ELF、不放宽成两个目标均接受。

Python 校验 ELF64 little-endian、AMDGPU、ET_DYN、section/program header、PT_LOAD、SHT_NOTE，以及 AMDGPU type32 metadata。MsgPack 子集有深度、数量、边界、编码和重复键检查，要求版本、非空 kernel、name/symbol/kernarg size。

限制：它不是完整 AMDHSA metadata/descriptor/symbol 一致性或指令语义验证。C++ 旧 loader 没有完整接入 Python 新 metadata 检查。真正 gfx1200 编译产物缺失，相关测试 SKIP。

### 4.7 离线状态机

```text
Unknown
   → PciMatched
   → ProfileValidated
   → DiscoveryValidated
   → FirmwareRequirementsValidated
   → OfflineReady

任何校验失败 → Failed，保存明确错误
```

ProfileValidated/OfflineReady 仅表示当前离线模型的检查通过，不表示真实硬件 profile、固件签名或加载已经验证。

状态机拒绝篡改的 profile，并拒绝重用非 fresh session。Failed 不会转成硬件授权；当前没有启动、MMIO、firmware upload 或队列创建状态。

### 4.8 Cobalt/RADV 模拟设备信息协议

当前 `N44I` wire v1 为 32 bytes little-endian，包含 magic/version/size、vendor/device、revision、revision 有效位、target、capabilities=0、reserved=0。

decode 检查长度、版本、target 和能力位；未验证的活跃 topology 不编码并明确拒绝。Unknown 用有效位表示，不能把零填充值当已发现的硬件参数。

这是纯内存 round-trip 原型，**不是 Cobalt N48N 兼容 ABI**，没有 IOUserClient、selector、transport、BO、提交或 fence。后续仍需设计生产 ABI。

<a id="tests"></a>

## 5. 实际离线测试结果

### 5.1 最终执行结果

| 状态 | 数量 | 含义 |
|---|---:|---|
| PASS | 56 | 测试确实执行并满足断言；包括逻辑和静态检查 |
| FAIL | 0 | 没有记录失败或运行错误 |
| SKIP | 2 | 缺真实 fixture/编译产物，未执行相应验证 |
| NOT RUN | 不计入 58 项 | C++、kext 和全部硬件验证 |
| 合计 | 58 | 56 PASS + 2 SKIP |

最后日志记录运行时间约 0.023 秒；这是小规模纯 CPU 测试，不是性能基准。

### 5.2 按类别统计

| 类别 | 总数 | PASS | SKIP |
|---|---:|---:|---:|
| ProfileTests | 6 | 6 | 0 |
| ParserTests | 22 | 21 | 1 |
| FirmwareTests | 11 | 11 | 0 |
| ElfTests | 11 | 10 | 1 |
| AbiTests | 4 | 4 | 0 |
| SafetyTests | 4 | 4 | 0 |
| 总计 | 58 | 56 | 2 |

### 5.3 实际命令

在实验目录执行的 CPU-only 最终测试命令：

```powershell
$env:TMP = Join-Path $PWD 'tmp'
$env:TEMP = $env:TMP
& 'D:\RuntimeEnvironment\mise\mise\data\installs\python\3.12.13\python.exe' -I -B run_offline.py
```

`run_offline.py` 写入 `reports/test-log.txt`、`reports/test-results.json`，不调用上游脚本或 GPU API。

实际补丁检查等效命令：

```powershell
git -c safe.directory='D:/CodexWorkSpace/黑苹果研究/Hackintosh-Navi44-Lab/upstream/AMDRadeonRDNA4' -c core.hooksPath=NUL -C upstream/AMDRadeonRDNA4 apply --check ../../patches/navi44-offline-prototype.patch
```

结果 PASS，仅校验，不应用。上游两仓库的 `git status --porcelain` 在检查时为空。

### 5.4 覆盖与强度

已执行：识别/未知设备/revision、格式/checksum/范围/重叠/重复、所有合成 Discovery 截断长度、1000 次固定随机种子的输入变异、32/64 地址、GC mismatch、固件缺失/错误、ELF target/metadata、ABI 和失败状态。

1000 次输入变异属于健壮性检查，不是完整覆盖引导 fuzz；没有 C++ sanitizer、动态内存检查或真实硬件故障注入。

SafetyTests 检查 host import 白名单、CMake 源列表、init 门禁位置和固定 LLVM 常量。它们是静态回归证据，不能证明操作系统层面的安全隔离。

### 5.5 SKIP 与 NOT RUN

| 项目 | 状态 | 原因 |
|---|---|---|
| 真实 RX9060XT Discovery fixture | SKIP | 未持有可靠实机捕获；禁止硬件读取 |
| 真正 gfx1200 shader 产物 | SKIP | 缺实际编译产物与工具链 |
| C++ host 编译/测试 | NOT RUN | 未找到可用 compiler/CMake |
| 完整 macOS kext 构建 | NOT RUN | 无 Apple SDK；目标被禁用 |
| MMIO、firmware、队列 | NOT RUN | 未授权且没有离线硬件后端 |
| 显示/Vulkan/Metal/WindowServer | NOT RUN | 未部署、未接入真实 macOS/GPU |

测试范围不可扩张为“RX 9060 XT 驱动已经通过”。

<a id="quality"></a>

## 6. 代码质量、安全边界与风险

### 6.1 三种防护的区别

| 层次 | 本轮措施 | 能防范 | 不能证明 |
|---|---|---|---|
| 构建隔离 | host CMake 只链接 codeobj/ipdiscovery/test | 正常 host target 不引入硬件实现 | 原始参考树所有函数均安全 |
| 源码/运行门禁 | Navi44 不绑定；init 授权恒 false；Makefile 禁用 | 正常误用构建/初始化路径 | 任意人为改源码后的安全 |
| OS 权限 | 使用现有 workspace-write 执行限制 | 约束部分文件操作 | 新建了只允许 lab 的独立 sandbox |

当前会话允许的文件写入范围大于 lab，因此没有声称建立新的 OS 级实验目录专属沙箱。源码门禁不能替代 OS 沙箱。

### 6.2 未审计或未完成部分

1. C++ 改动没有编译，不能排除语法、ABI、链接或平台问题。
2. Python 与 C++ 实现不同，不能互相代替回归。
3. Parser 版本范围较保守，真实数据可能被拒绝，需 fixture 验证。
4. Firmware 规则、CRC、签名和 package 格式不完整。
5. ELF/MsgPack 只支持必要子集，不覆盖所有编译器输出。
6. 原仓库硬件模块和大型源码没有完成全部安全审计。
7. 测试里的非 GC IP 版本、SE/RB、payload 均是合成示例。
8. Cobalt 模拟 ABI 不构成真实移植；私有 Metal 接入和 shader cache 可复现性仍未解决。

### 6.3 许可证

新增代码沿用 AMDRadeonRDNA4 的 BSD-3-Clause；原 LICENSE 保留。Linux Discovery 参考头保留 AMD MIT 声明；LLVM 参考保留原声明。

Cobalt 顶层 MIT 不替代子目录和依赖许可证。Mesa、LLVM、转译组件、固件要分别审查。当前没有复制私有 Apple 框架、没有下载固件镜像，不生成任何伪造签名。

### 6.4 安全记录的准确措辞

本项目没有主动修改 Windows、EFI、分区或 GPU 状态。该结论来自已执行命令和代码范围记录，不是第三方操作系统审计证明。

正常 OS、工具和联网缓存仍可能发生；不能承诺物理零写入。完整上游树包含危险脚本，未执行，应继续作为参考而非安装入口。

<a id="acceptance"></a>

## 7. 当前功能等级与验收判断

### 7.1 功能状态

| 功能 | 当前实际等级 |
|---|---|
| PCI 识别 | Python 离线 PASS；C++ 已编码未编译 |
| Hardware Profile | 静态型号/目标模型；revision/topology 未实机验证 |
| Discovery | Python 32/64 离线 PASS；C++ 32 位加固未编译，64 位明确拒绝 |
| Firmware 选择 | 输入 IP 需求模型及合成结构 PASS；实际固件规则/签名未验证 |
| gfx1200 Target | 常量重新核对；离线交叉目标拒绝 PASS |
| 基础显示 | 未开发验证本机输出；NOT RUN |
| GPU 命令提交 | 没有本阶段硬件接入；NOT RUN |
| Vulkan | 无本机提交；NOT RUN |
| Metal | 无本机接口执行；NOT RUN |
| WindowServer | 无真实 macOS 合成验证；NOT RUN |

### 7.2 用户验收项逐条对应

| 验收项 | 本轮结论 |
|---|---|
| 1. 独立目录与实际代码 | 完成 |
| 2. 根据真实上游实现基础适配 | 源码级完成；编译/硬件未完成 |
| 3. 区分 gfx1200/gfx1201 | 离线完成 |
| 4. Profile/firmware 需求 | 完成模型；实际硬件/固件验证未完成 |
| 5. Discovery 离线实现/改进 | Python 完成测试；C++ 编码待编译 |
| 6. 单元/回归测试 | Python 实际运行；C++ 测试已写未运行 |
| 7. 运行允许的测试 | 完成 58 项记录 |
| 8. 记录不可运行项 | 完成 SKIP/NOT RUN |
| 9. 不默认初始化 RX9060XT | 源码与构建门禁完成；不作为硬件实测结果 |
| 10. 代码变更报告 | 完成 |
| 11. 显示缺口 | 已明确 |
| 12. Vulkan/Metal 缺口 | 已明确 |
| 13. 不主动修改系统/项目外用户文件 | 已执行工作遵守该范围；非外部审计证明 |
| 14. 不加载驱动 | 未执行 |
| 15. 不操作分区/EFI | 未执行 |
| 16. 不访问真实 GPU 接口 | 未执行 |

本阶段可以认定“离线软件原型已交付”，不能认定全部驱动研发或原生 macOS 目标已经完成。

<a id="next"></a>

## 8. 下一阶段与剩余阻碍

### 8.1 优先继续的纯软件任务

| 任务 | 所需条件 | 验收 |
|---|---|---|
| C++ host 编译 | 可用、合法、经确认的现有工具链 | 编译无错误，CPU-only target 运行 |
| 交叉实现回归 | 相同格式 fixture | C++/Python 结果与拒绝行为可解释 |
| 64 位接口 | 设计独立 API，不破坏旧 uint32 接口 | 不截断，地址范围清楚 |
| Parser fuzz | 安全 CPU-only 环境 | 覆盖、故障记录及修复 |
| Firmware 格式 | 固定上游定义/合法静态样本 | CRC、package、组件与版本规则明确 |
| ELF/metadata 完整性 | 合法编译产物 | descriptor/symbol/metadata 一致性 |
| 生产设备 ABI | Cobalt 实际 ABI 审查 | 版本、有效位、权限、未知字段明确 |

本轮没有安装工具补齐这些条件。未来若需要安装依赖或扩大授权，应单独决定。

### 8.2 从离线走向真实显示的缺口

需要合法 macOS 构建环境、完整 kext 构建、板卡 revision/VBIOS/IP Discovery/端口映射/BAR/EDID 的可信资料，以及明确的实机测试授权。

实机阶段还要制定 Windows/第二盘保护、GPU 黑屏恢复、版本回退及人工观察路径。第二盘已有 Linux 分区，不能按空盘处理。

建议先继承启动显示和保守模式，再验证 EDID、模式切换、显示休眠和端口。不能直接开启 1440p180 或完整 GPU 初始化。

### 8.3 从显示走向 Vulkan/Metal 的缺口

- Navi44 各 IP 的准确固件与初始化。
- GPU VM、BO、队列、同步、中断、超时及 DMA 生命周期。
- gfx1200 真正编译产物与受控计算/图形验证。
- 真实 topology/GB_ADDR_CONFIG/VRAM/BAR → Darwin RADV。
- 单一 GPU 资源所有者，禁止两套内核初始化争用。
- Cobalt 对应 bundle/cache 的可复现性。
- Metal 资源、共享纹理、argument buffers 和私有系统 ABI。
- WindowServer、VideoToolbox、睡眠及长期回归。

上述功能没有因本轮离线测试而自动变得可用。

### 8.4 本轮停止点

完成代码、测试和报告后停止。没有启动 macOS 安装，没有加载任何驱动，没有解除初始化门禁，没有进行真实 GPU 实验。

<a id="appendix"></a>

## 附录 A：58 项实际测试清单

下表名称来自最终日志。PASS 是各测试范围内通过，不扩张为 GPU 功能验证。

| 类别 | 测试名 | 状态 |
|---|---|---|
| Profile | test_navi44 | PASS |
| Profile | test_navi48_regression | PASS |
| Profile | test_unknown_vendor | PASS |
| Profile | test_unknown_device | PASS |
| Profile | test_revision | PASS |
| Profile | test_hardware_never_authorized | PASS |
| Parser | test_basic | PASS |
| Parser | test_v2 | PASS |
| Parser | test_64bit | PASS |
| Parser | test_magic | PASS |
| Parser | test_version | PASS |
| Parser | test_truncations | PASS |
| Parser | test_length | PASS |
| Parser | test_binary_checksum | PASS |
| Parser | test_table_checksum | PASS |
| Parser | test_unknown_ip | PASS |
| Parser | test_duplicate | PASS |
| Parser | test_die_offset | PASS |
| Parser | test_address_overflow | PASS |
| Parser | test_integer_overflow | PASS |
| Parser | test_overlap | PASS |
| Parser | test_ip_version | PASS |
| Parser | test_base_count | PASS |
| Parser | test_gc_mismatch | PASS |
| Parser | test_gc_unknown | PASS |
| Parser | test_navi48 | PASS |
| Parser | test_mutation_robustness | PASS |
| Parser | test_real_navi44_fixture | SKIP |
| Firmware | test_manifest | PASS |
| Firmware | test_missing | PASS |
| Firmware | test_wrong_ip | PASS |
| Firmware | test_duplicate | PASS |
| Firmware | test_bad_size | PASS |
| Firmware | test_unknown_header | PASS |
| Firmware | test_crc_unverified | PASS |
| Firmware | test_payload_inside_header | PASS |
| Firmware | test_state_machine | PASS |
| Firmware | test_failed_cleanup | PASS |
| Firmware | test_tampered_profile | PASS |
| ELF | test_gfx1200 | PASS |
| ELF | test_gfx1201_regression | PASS |
| ELF | test_cross_target | PASS |
| ELF | test_unknown | PASS |
| ELF | test_truncated | PASS |
| ELF | test_no_metadata | PASS |
| ELF | test_empty_metadata | PASS |
| ELF | test_missing_kernel_identity | PASS |
| ELF | test_overflow | PASS |
| ELF | test_bad_magic | PASS |
| ELF | test_real_shader | SKIP |
| ABI | test_roundtrip | PASS |
| ABI | test_caps_rejected | PASS |
| ABI | test_unknown_geometry | PASS |
| ABI | test_bad_version | PASS |
| Safety | test_host_imports_have_no_hardware_backend | PASS |
| Safety | test_build_excludes_hardware | PASS |
| Safety | test_init_guard_precedes_hardware | PASS |
| Safety | test_pinned_llvm_constants | PASS |

## 附录 B：来源与证据

| 来源 | 链接/版本 | 本轮用途 |
|---|---|---|
| AMDRadeonRDNA4 | [49f7f20 固定快照](https://github.com/RX4Darwin/AMDRadeonRDNA4.kext/tree/49f7f20c00dd154384418078f8a09e79c400a06a) | 开发基础、BSD-3-Clause |
| Cobalt64 | [d6c9aed 固定快照](https://github.com/Almosst-DEV/Cobalt64/tree/d6c9aedf8e6526a39e349b5886cbc8c7ddf77f65) | ABI/后续接入参考 |
| Cobalt PR #12 | [PR 页面](https://github.com/Almosst-DEV/Cobalt64/pull/12) | 状态复查，未合并未应用 |
| Linux Discovery | [固定头文件](https://github.com/torvalds/linux/blob/24a19b953e2a3d0ea5a8c4951a0ab8f32720c907/drivers/gpu/drm/amd/include/discovery.h) | 格式和结构定义 |
| LLVM ELF | [固定头文件](https://github.com/llvm/llvm-project/blob/87f0227cb60147a26a1eeb4fb06e3b505e9c7261/llvm/include/llvm/BinaryFormat/ELF.h) | 0x048/0x04e 重新核验 |
| RADV | [官方架构资料](https://docs.mesa3d.org/drivers/radv.html) | 后续 UMD/KMD 分工背景 |

本轮源码证据属于可审查实现；本轮测试证据仅是 host 数据和逻辑。没有新增 Navi44 实机证据。

## 附录 C：参考文件和关键产物 SHA-256

| 文件 | SHA-256 |
|---|---|
| linux-discovery.h | `032d97c699c9378edb64b005ddc53ab08763b853f6b64fcdb0a71dd7999b98e5` |
| llvm-ELF.h | `ff0685fe6d5a62a2df2df41eb278330153e2d0a52e573ae02cdcd56c3b6b579c` |
| asicprofile.hpp | `6a668afab45dc24be0894dd35b819897752e3661df1b5b781e766fe62018f674` |
| host/navi44.py | `f5045fb7b22de9df3c6eef6b421807a8da0406a18c7fbb2d5f866da513e2d9eb` |
| tests/test_offline.py | `d36ca25b282f37be865411f2945b11bd47d0031402236a872418637b9321cd19` |
| navi44-offline-prototype.patch | `f91bc73d1f91a8d9808f2272cc2b93967a4c1548be01cc090c00afec992796fb` |

以上用于识别本轮产物，不是签名、安全认证或对未来改动的保证。机器可读记录见 [provenance.json](provenance.json) 与 [artifact-sha256.json](artifact-sha256.json)。

---

**最终结论：已交付实际存在、可审查、具有运行结果的 Navi 44 离线适配软件原型。已执行的验证仅覆盖 Python host 逻辑及静态检查；C++、真实固件、显示和 GPU 加速仍需未来验证。本轮没有进行任何部署或硬件实验。**
