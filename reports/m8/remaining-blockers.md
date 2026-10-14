# M8 剩余阻碍

- DisplayID未实现；经典EDID DTD clock无法表达1440p180，不能宣称本监视器完整解析。
- EDID只支持1.3/1.4及CTA rev3子集；interlace/stereo/FRL/DSC/HDR/VRR/完整VIC仍未支持。
- Atom只支持限定header/master/display版本与静态记录，没有真实Navi44 ROM或PHY routing证据。
- 原始checksum/静态元数据不是固件签名或真实硬件能力证明。
- CRC-32 ISO-HDLC算法已实现，但AMD固件具体格式/convention缺少可信样本确认，默认拒绝路径不放宽。
- ELF只有离线验证/预算，没有GPU loader/ISA执行；真gfx1200编译产物继续SKIP。
- Node对象生命周期已通过typed pool改造；真实Darwin OSData retain/线程gate/heap pool/teardown仍未接入。
- native Apple API源码未编译，Windows COFF检查不能替代Mach-O、内核符号/总栈/SDK兼容。
- N44Q是数据候选，无真实IOUserClient认证或全局GPU owner；N48N1.9与Cobalt1.12不能混用。
- GPU power/firmware/DCN/DMUB/GOP/AUX/VM/queue/恢复完全未执行；显示/Vulkan/Metal/WindowServer NOT RUN。
- Sanitizer只覆盖有限输入，leak/concurrency/hardware stability没有验证，fuzz非coverage-guided。

M9优先真实macOS CPU编译/fixture验证；随后再判断是否有条件进行独立kext或硬件研发。
不存在本轮授权可自动启动的GPU实验或Mac远程操作。
