# M8 Cobalt Production ABI candidate

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
