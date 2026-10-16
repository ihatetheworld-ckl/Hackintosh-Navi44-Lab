# 显示路径：容器校验和理论预算

新增displayid.hpp/.cpp依据固定Linux24a19b953e2a3d0ea5a8c4951a0ab8f32720c907
的MIT DisplayID验证/格式参考独立实现，不编译Linux头。版权/许可见NOTICE及
licenses/DisplayID-reference-MIT.txt，原始参考留local，公开只记录pin/hash。

范围仅单个128B EDID DisplayID扩展：0x70、1.2/1.3/2.0结构版本、双checksum、
payload/block边界、primaryUse范围、零padding及固定32块容量。continuation拒绝。
结果是opaque块目录，不解释Type I/VII/动态时序/DSC/VRR，不自动接入既有EDID
模式集合。结构PASS不表示完整DisplayID语义受支持，所有timing/output标记保持false。

DisplayPlan复用现有timing/assess，拒绝未知/未建模connector、链路种类不匹配、
伪造routingKnown/hardwareVerified及未知pixel编码。缺链路参数保持Unknown。
合成2560×1440@180、hTotal2720/vTotal1480理论pixel clock724608kHz；
24bpp需要17.390592Gbit/s，合成DP HBR3×4 payload25.92Gbit/s预算可容纳。
这不是EDID实测、Navi44 DCN能力、PHY训练或画面输出证据。

真实显示仍缺可信connector/EDID/DisplayID数据、GOP状态、DCN/DMUB/PLL/PHY/
AUX/HPD、固件协议、Framebuffer与macOS图形接口。无核显后备条件不能忽略。
Link Training、DSC、VRR、scanout、Metal和1440p180实际输出均NOT RUN。
