# Navi 44 (`gfx1200`) 与 Navi 48 (`gfx1201`) 硬件与驱动差异模型

- **文档版本**：M5 / M9-prep (2026-10-26)
- **目标硬件**：Gigabyte AMD Radeon RX 9060 XT 16GB (`PCI\VEN_1002&DEV_7590&SUBSYS_24381458&REV_C0`)
- **上游参考基线**：
  - `RX4Darwin/AMDRadeonRDNA4.kext` (`49f7f20c00dd154384418078f8a09e79c400a06a`)
  - `Almosst-DEV/Cobalt64` (`d6c9aedf8e6526a39e349b5886cbc8c7ddf77f65`)

---

## 1. 架构与硬件参数对比表 (`gfx1200` vs `gfx1201`)

| 维度 | Navi 48 (`gfx1201` / RX 9070 XT) | Navi 44 (`gfx1200` / 本机 RX 9060 XT) | 证据状态与来源 | 驱动适配影响 |
|---|---|---|---|---|
| **PCI Vendor:Device** | `1002:7550` / `1002:7551` | **`1002:7590`** | `VERIFIED_REAL_HARDWARE` (Windows PCI Enum) | `Info.plist` `IOPCIMatch` 与 `Asic::identify` 必须精确匹配 `0x75901002` |
| **PCI Revision ID** | `0xC0` / `0xC8` (视板卡而定) | **`0xC0`** | `VERIFIED_REAL_HARDWARE` | 已在 `N44I v2` / `N44Q 1.0` / `CobaltQueryProjection` 中建模 |
| **PCI Subsystem ID** | `1DA2:E490` (Sapphire 参考卡) | **`1458:2438` (Gigabyte)** | `VERIFIED_REAL_HARDWARE` | 板级 AtomBIOS `DisplayObjectInfo` 连接器映射可能与蓝宝石参考卡不同，禁止硬编码连接器路由 |
| **PCIe 桥拓扑** | CPU PEG → Switch US (`1002:1478`) → Switch DS (`1002:1479`) → GPU | Bus 0 `(0,1,0)` → Bus 1 `1002:1478` → Bus 2 `1002:1479` → **Bus 3 `1002:7590`** | `VERIFIED_REAL_HARDWARE` | RDNA4 内部集成 PCIe Switch，ACPI 路径为 `PC00.PEG0.PEGP.SWUS.SWDS.GFX0` |
| **ELF Machine / Target** | `EM_AMDGPU` (`224`), `e_flags & 0xff == 0x4e` (`Gfx1201`) | `EM_AMDGPU` (`224`), **`e_flags & 0xff == 0x48` (`Gfx1200`)** | `VERIFIED_HOST_ONLY` (`llvm-ELF.h` `EF_AMDGPU_MACH_AMDGCN_GFX1200 = 0x048`) | Shader / Code Object 校验器严格区分 `0x48` 与 `0x4e`，禁止混用 |
| **GC (Graphics/Compute) IP** | `GC 12.0.1` (`HwGc = 11`) | **`GC 12.0.0`** (`HwGc = 11`) | `UPSTREAM_REPORTED` (Linux AMDGPU / Mesa) | 固件文件前缀为 `gc_12_0_0_{pfp,me,mec,rlc,imu,mes,mes1}.bin`；本机真实 IP Discovery 二进制尚待 Gate D 只读采集确认 |
| **Shader Engine / CU / RB** | 4 SE × 16 CU = 64 CU, 16 RB | 公开规格：2 SE × 16 CU = 32 CU, 8 RB (本机真值待 IP Discovery `gcInfo` 确认) | `UNVERIFIED` (本机寄存器/Discovery 未读) | `profile.topology.verified` 保持 `false`，禁止用硬编码的 Navi48 拓扑欺骗 RADV |
| **`GB_ADDR_CONFIG`** | `0x00000344` / `ACD_GB_ADDR_CONFIG_GFX1201` (4 SE / 16 RB tiling) | 随 2 SE / 8 RB / 128-bit 位宽变化（待本机真机读取） | `UNVERIFIED` | **关键阻碍点**：Cobalt64 `patch 0007` 在 `acd_native_handshake()` 中硬编码校验 `ACD_GB_ADDR_CONFIG_GFX1201`，必须改为根据 `gfx1200` 动态接受合法配置 |
| **VRAM 与 BAR** | 16 GB GDDR6 (256-bit) | **16 GB GDDR6** (`17,095,983,104 B`, 128-bit) | `VERIFIED_REAL_HARDWARE` (Windows Registry `qwMemorySize`) | 支持 16GB 大显存池建模 (`vramVisTotal` / `vramHiTotal`) |
| **DCN (Display Engine)** | `DCN 4.0.1` (`HwDmu = 271`) | `DCN 4.0.1` (`HwDmu = 271`，待本机 Discovery 核实) | `UPSTREAM_REPORTED` | GOP Framebuffer 接管与 HUBP0/OTG0 扫描输出寄存器族同属 DCN4，但时钟/PHY 路由需按本卡 AtomBIOS 解析 |
| **SDMA / PSP / SMU** | `SDMA 7.0.x` (`HwSdma0=42`), `PSP 14.0.x` (`HwMp0=255`), `SMU 14.0.x` (`HwMp1=1`) | 待本机 IP Discovery 精确确认 minor/revision | `UNVERIFIED` | `NaviCore::firmwareRequirements()` 通过动态读取 `IpDiscovery` 表推导所需固件版本，不硬编码 Navi48 固件名 |

---

## 2. 上游 `AMDRadeonRDNA4` 与 `Cobalt64` 代码复用与重写边界 (Section 7.3 & 7.4)

### 2.1 可直接抽象复用的公共 RDNA4 模块（已在本仓库 `core/` 与 `src/` 验证）
1. **无异常 / 无 RTTI / Freestanding 解析核心**：
   - `src/ipdiscovery.cpp`：AMD IP Discovery 二进制解析（支持 32-bit 与 64-bit `IpEntry64` 寄存器基址计算）。
   - `src/atombios.cpp`：AtomBIOS 2.2/2.3 数据表、Master Table、DisplayObjectInfo v1.5、`DisplayPath` 与 I2C/HPD Record 解析。
   - `src/edid.cpp` + `core/display.cpp`：E-EDID 1.3/1.4、CTA-861-G 扩展块、**本轮新增的 DisplayID v1.3/v2.0 Type I/VII 高刷详细时序解析**、以及 DP 8b/10b 与 HDMI TMDS 链路带宽算术预检。
   - `src/codeobj.cpp` + `core/validation.cpp`：AMDGPU ELF (`EM_AMDGPU=224`) Note/MsgPack 元数据、Kernel Descriptor (`.kd`) 与 PSP Firmware 包结构校验。
   - `core/integrity.cpp`：CRC-32 ISO-HDLC 载荷校验（将 `checksumMatched` 与 `signatureVerified`/`loadable` 严格解耦）。

### 2.2 必须针对 Navi44 (`gfx1200`) 隔离或重写的部分
1. **上游 `src/device.cpp` / `src/plugin.cpp` 中的 Navi48 硬编码假设**：
   - 上游 `AMDRadeonRDNA4.kext` 的 `Makefile` 与 `device.cpp` 直接嵌入了 `Sapphire.RX9070XT` 的固件 blob 引用（`fwblobs.S` 指向 `navi48_*`）以及针对 `1002:7550` 的 S1b/S1c 测试门禁。
   - 在 Navi44 适配中，**严禁**将 `navi48` 的 `gc_12_0_1` / `psp` / `smu` 固件上传到 `1002:7590` (`gfx1200`) 硬件！
2. **Cobalt64 / Mesa RADV Darwin Backend (`mesa-patches/0001..0009`) 的 Navi48 耦合点**：
   - `0001-radv-Darwin-macOS-backend-with-canned-gfx1201-device.patch`：包含 `canned gfx1201` 假设备描述。
   - `0002-radv-Darwin-native-backend-Mesa-half-of-the-Navi48-k.patch` 与 `0007-radv-darwin-take-GB_ADDR_CONFIG-fr...patch`：在 `acd_native_handshake()` 中检查 `n48n_info` (192B)，但强制比对 `ACD_GB_ADDR_CONFIG_GFX1201`。
   - **本轮已完成的安全演进**：在 `core/query_candidate.hpp/.cpp` 中实现了 `projectToCobaltInfo()` 与 `decodeCobaltProjection()`，将经过验证的 `N44Q 1.0` (128B) 显式投影到 192B `n48n_info` 兼容布局（在 `reserved[0..7]` 写入 `'N44P'` 签名、`1002:7590`、Target `0x48`、Presence 掩码与单调 Epoch），同时强制离线状态下 `flags == 0`、`vramVisFree == 0`、`vramHiFree == 0`，防止任何未验证数据触发 RADV 真实队列提交或伪造硬件就绪状态。

---

## 3. Metal 支持的真实技术距离与缺失层清单 (Section 7.4)

遵循项目规范“不把 Vulkan 当作 Metal，不伪造 Metal 支持”的原则，当前在 macOS 26 Tahoe 上为 RX 9060 XT 实现 Metal 加速所缺失的完整链路如下：

1. **Layer 1 — 内核显示与命令提交层 (`AMDRadeonRDNA4-Navi44.kext`)**：
   - 缺失项：在真机 macOS 26 下完成 `1002:7590` 的 BAR0 MMIO 映射、IP Discovery 实测、PSP/SMU/GC 12.0.0 固件加载、GART/VRAM 页表建立、GFX12 Ring 命令提交与 `IOAccelNavi48NativeClient` (或 `Navi44`) UserClient 暴露。
   - 当前状态：`NOT RUN`（等待 Mac 原生编译 + Gate D 授权）。
2. **Layer 2 — 用户态 Vulkan 驱动层 (`Mesa RADV Darwin`)**：
   - 缺失项：将 Cobalt64 的 Mesa 补丁更新以支持 `CHIP_GFX1200` (`Navi44`) 的 `radv_physical_device` 初始化、BO 分配/导入 (`BoImportHost`)、GFX12 命令流生成与 Syncobj/Fence 同步。
   - 当前状态：协议层投影已通过离线测试 (`VERIFIED_HOST_ONLY`)，真机 `VkDevice` 初始化 `NOT RUN`。
3. **Layer 3 — Metal-on-Vulkan 转换与 WindowServer 接入层 (`metal2vulkan` + `Navi48MetalNub`)**：
   - 缺失项：macOS `WindowServer` 需要通过 `IOAccelerator` / `MTLDevice` bundle 接口调用 GPU。Cobalt64 采用 `Navi48MetalNub` + 用户态 `metal2vulkan` 转换层将 Metal API 与 AIR/MSL Shader 转换为 Vulkan/SPIR-V 执行，并通过 `N48N_SEL_SCAN_PRESENT` 翻转屏幕。
   - 当前状态：在 Navi44 上完全属于 **`BLOCKED` / `UNVERIFIED`** 阶段。在 Layer 1 与 Layer 2 真机验证通过前，绝不启用 `navi48-metal=1` 或声称具备 Metal 加速。
