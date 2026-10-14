# 未完成与阻碍

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
