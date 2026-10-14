# M7 Navi 44 显示研发就绪度

## 确认与未知

用户确认 RX 9060 XT，PCI 1002:7590；现有 Asic profile 的 gfx1200 / GC 12.0.0 是家族预期。
Navi48 对照 gfx1201 / GC 12.0.1；不可将对照 ROM、固件、CU 数和寄存器常量复制成 Navi44 实测数据。
本轮没有读取本机 ROM、IP Discovery、PCI BAR、MMIO、EDID 或硬件电源状态。
所有当前自动化样本是合成数据；non-GC IP 版本和 topology 是刻意构造的测试值。

## 可复用源码位置（仅静态阅读）

src/ipdiscovery.cpp：版本、校验和、IP 与寄存器段地址解析；没有实际寄存器访问。
src/edid.cpp/.hpp：已有无 IOKit 的 EDID 纯逻辑，下一轮可加入 CPU allowlist 与恶意样本回归。
src/atombios.cpp：板卡连接器、固件表数据依赖，不能以其他板卡的样本代替本卡。
src/dmub.hpp、dptrain.cpp、dpphy.cpp、modeset.cpp、pipe.cpp、otgtiming.cpp、
ndrv.cpp：后续显示路径参考，当前没有编译/执行其硬件路径。

## 距基础输出仍缺少的具体条件

| 条件 | 当前状态 | 未来验收 |
|---|---|---|
| Navi44 真实 IP/拓扑与固件映射 | 缺少板卡样本 | 合法静态输入可重现解析；未知字段仍不可用 |
| GOP framebuffer 格式/stride/地址所有权 | 未确认 | 首先审查安全继承方案，证明不覆盖正在使用的平面 |
| EDID、连接器、DP AUX/HDMI DDC 与链路能力 | 未确认 | 先离线模式解析，再独立授权链路实验 |
| DCN/DMUB 与支持的精确 IP 版本 | 未确认板卡值 | 对比公开 amdgpu 接口，拒绝猜寄存器值 |
| 显存映射、firmware 状态、时钟与电源 | 未确认 | 单一资源所有者、超时、失败停止与恢复路径 |
| IONDRVFramebuffer / WindowServer 接入 | 未构建 | 真 macOS 编译，再独立 GPU 测试 |

本轮 Native adapter 只有 CPU 内存/日志接口，不能建立 framebuffer 输出。
基础显示、模式切换、热插拔、显示休眠、多屏、Metal 和 WindowServer 都是 NOT RUN。

## 1440p180 的量化边界

2560×1440×4 = 14,745,600 字节/完整 32bpp 帧；
180Hz 单次全屏写入约 2.65 GB/s（约 2.47 GiB/s），尚未计读回、alpha 合成及复制。
180Hz 帧时间约 5.56ms。这是纯算术下限，不是 GPU/CPU 测得性能。
有效像素约 663.6 Mpixel/s；链路还需要 blanking / encoding 与色深开销。
扫描输出速率、窗口合成速度、实际呈现帧率分别验收；解析通过不能证明任一项。

未来若丢失显示、DMUB 无响应、时钟/链路不一致或超时，立即停止后续初始化与提交，
不得循环重试猜测寄存器。软件恢复无法承诺恢复唯一显卡的黑屏，需额外人工恢复方案。
