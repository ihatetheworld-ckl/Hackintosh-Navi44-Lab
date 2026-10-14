# M8 Display Capability / Mode / Link Model

~~~mermaid
flowchart LR
    E[EDID CPU bytes] --> M[Monitor declarations / Modes]
    R[Static Atom ROM bytes] --> C[Connector descriptions]
    M --> A[Pure mathematical assessment]
    C --> F[Future connector / PHY adapter: not implemented]
    L[Independent link budget] --> A
    G[Independent engine budget] --> A
    A --> U[No output permission / no hardware verified capability]
~~~

核心函数：NaviDisplay::timing、edid、connectors、assess。
Mode包含完整DetailedTiming、约分后的64位refresh fraction、source与同频替代标志。
Monitor包含mfg/product、digital、partial、声明的TMDS/SCDC与计数，不包含用户serial。
Connector包含原object/encoder/tag、静态I2C/HPD记录；routingKnown/boardVerified均false。

Origin = Unknown / Synthetic / StaticReference，只记录来源声明，不是认证。
没有从字节数据产生DeviceVerified的枚举值。不能伪装本机测试。
输入/输出缓冲由调用方持有，不应相互重叠；Core无IO或隐式allocation。

数学规则：geometry/sync与blanking一致，progressive，clock范围1000..2500000kHz，
刷新率实验预算1..1000Hz。它们是本原型预算，不是AMD/DP的正式最大能力。
refresh = pixelClockKHz×1000 / (hTotal×vTotal)，64位整数约分。
判断RGB24/30/36bpp；DP8b10b只接受已知lane数1/2/4与1.62/2.7/5.4/8.1Gbps；
payload按8/10计算。TMDS假设RGB/4:4:4，payload=characterClock×24，深色占用更高。
引擎clock单独比较。未知证据不产生WithinBudget。
WithinBudget只代表理想算术上限，未计算完整protocol/audio/control/FEC/blanking分配，也不是链路可用证明。
不支持UHBR128b132、HDMI FRL、DSC、YCbCr subsampling、VRR或训练。
任何结果outputAllowed/hardwareVerified始终false。

frameBytes=activeW×activeH×4；fullFrameBytesPerSecond为按刷新分数计算的向上取整写带宽。
乘法溢出直接拒绝。timing()复制输入后清空输出，支持input与out.timing别名的再验证。

## 1440p180

2560×1440×180=663552000有效像素/秒，尚未计消隐。
经典EDID DTD的16位10kHz clock上限655350kHz，低于该数值；
因此不能用经典DTD表达本目标，必须进一步研究DisplayID/其他合法表达。
本轮DisplayID不支持，不能宣称已解析本显示器180Hz。
合成模型2720×1500 totals / 734400kHz严格算得180Hz，只用于数学测试，不是实际输出参数建议。
32bpp完整帧14745600B，180fps一次写带宽2654208000B/s、帧时间约5.56ms。
没有GPU/CPU性能测量，扫描速率、合成与实际present帧率需各自未来验收。
