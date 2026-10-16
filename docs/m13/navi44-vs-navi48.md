# Navi44 与 Navi48：静态事实和未知

已有ASIC表区分7590/Navi44/gfx1200/预期GC12.0.0与7550/7551/Navi48/gfx1201/
预期GC12.0.1。识别不是采样或初始化授权，revision/topology/capabilities仍未验证。
[AMD GPU架构资料](https://rocm.docs.amd.com/en/latest/reference/gpu-arch-specs.html)
可作为产品/ISA家族参考，不能证明当前板卡具体布线、固件或macOS支持。

固定AMD衍生pin49f7f20c、Cobalt pin d6c9aedf、LLVM/Linux/Mesa参考和许可证保留。
现有Navi48 DCN4.1/GOP pipe、GB_ADDR_CONFIG、ring/VM/PSP及canned gfx1201参数
都只是STATIC_REFERENCE_ONLY。N44I96B/N44Q128B不等于N48N生产协议；AMD
minor9与Cobalt minor12/QueryInfo192B不得按名字混用。

| 主题 | 可以静态确认 | Navi44仍缺 |
|---|---|---|
| ISA/Code Object | 不同gfx目标需分别验证ELF标志 | 真实gfx1200程序及Shader/CP运行，改名字不证明可执行 |
| IP Discovery | 有界解析器及拓扑模型 | 实卡IP实例、基址、revision、harvesting |
| firmware/PSP/DMUB | 元数据与范围/格式检查 | 合法版本、签名/握手、时序与固件dialect |
| 显示引擎 | EDID/CTA/connector与预算纯模型 | Navi44 DCN/PHY/时钟/HPD/AUX/连接器布线及训练 |
| GPU Memory/VM | 本轮CPU地址/Fence账本 | 实际VRAM、BAR、页表格式/VMID/TLB/映射同步 |
| Command Processor | 保留上游参考源码但不执行 | 队列协议、包格式边界、fence、IRQ、超时与reset恢复 |

未知硬件字段保持UNKNOWN/REQUIRES_REAL_NAVI44_DATA，不填Navi48常量。
真实硬件、Windows或唯一显示卡上的任何实验均需未来独立授权和恢复条件。
