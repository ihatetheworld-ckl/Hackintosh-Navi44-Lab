# M7 Cobalt / RADV 数据接口准备

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
