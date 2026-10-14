# M6.5 剩余阻碍与下一阶段

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
