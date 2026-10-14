# M8 EDID Parser

继续复用 src/edid.cpp/.hpp 的字段、DMT/VIC表与CTA解码，没有增加第二套原始EDID解析器。
Core/display.cpp 提供严格的整包验证与 Mode/Monitor 模型，旧宽松诊断入口不能当生产能力验证。

支持范围：EDID 1.3/1.4，精确128字节块、Header、Checksum、manufacturer三字母编码/product，
最多基础块加3扩展；digital标志、progressive数字separate-sync DTD、
已有DMT的established/standard timing子集、CTA revision3的VIC表子集与DTD。
支持HDMI LLC/Forum VSDB的TMDS/SCDC声明字段；不控制SCDC，也不认为链路已训练。

新增严格拒绝：坏checksum/header/version、声明长度不一致、跨界DBC、非法DTD offset、
零offset却携带数据、短HDMI Forum block、重复vendor能力块、SVD容量耗尽、
sync超过blanking、零尺寸/宽度、超预算或不支持的signal。
源解析器的parseDetailedTiming失败清空结果；parseCtaBlock错误不返回部分成功。
Core edid()失败清空Monitor和调用方Mode存储。调用方保证输入、输出不重叠并存活。

不支持：EDID2、DisplayID、interlace/stereo/border/analog-composite DTD、完整HDR/FRL/DSC/VRR、
所有VIC、GTF/CVT公式。未知extension默认Unsupported；
KnownBlocksOnly策略仅保留已知块并标记partial；未解析的timing也计入unresolved/partial。
未知CTA vendor/extended payload不会被当作可用链路能力。
标准timing的DMT解析标记来源；Core不沿用EDID1.3“digital就支持RB”的隐式推断。

Mode.sources区分BaseDtd/CtaDtd/Established/Standard/CtaVic。
完全相同的raster、clock、sync、polarity去重并合并来源。
同尺寸同精确刷新率而timing不同，保留为sameRateAlternative，不能随意替换。
capacity不足返回Budget，不静默丢模式。hardwareVerified恒false。

测试fixture为自制合成字节，含规范中的1080p60 DTD数值；不是本机EDID，不包含用户serial。
所有扩展checksum校验。未通过DDC/I2C/AUX或Windows GPU API查询显示器。

格式参考：
[VESA E-EDID A2](https://glenwing.github.io/docs/VESA-EEDID-A2.pdf)，2006规范公开镜像；
[Linux v6.15 drm_edid.c](https://github.com/torvalds/linux/blob/v6.15/drivers/gpu/drm/drm_edid.c)，
对照DTD/CTA边界和HF块最小长度（2026-10-14阅读，E1/E2）。
没有复制Linux实现或引入其运行库。
