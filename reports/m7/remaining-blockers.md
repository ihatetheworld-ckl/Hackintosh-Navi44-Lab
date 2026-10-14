# M7 剩余阻碍

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
