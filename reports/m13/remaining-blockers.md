# M13 阻碍

- SDK26.5与公开XNU26.5已具备，原SDK目标缺口已缩小；实际目标二进制/KDK/build
  未取得，TARGET_BINARY_KPI_AUDIT/TARGET_ABI_CLOSURE仍BLOCKED，LOADABLE_KEXT未知。
- 26.7.1等较新正式版出现在官方列表，但没有对应完整SDK/XNU/二进制核验；
  静态26.5基线不决定最终安装版本。
- 真实OSObject/IOService、内核锁/waiter drain、Owner最终release/free未运行；
  Host测试不能证明Kernel Runtime。GPU BO/VRAM/映射/IRQ/Queue/Reset都没有实现。
- DisplayID只支持容器，不解码时序；预算不是训练/scanout证据。真实Navi44
  Discovery/connector/DCN/DMUB/firmware/内存参数与macOS图形集成仍缺。
- Windows/x86 Runtime/CMake未执行；不安装Rosetta、CMake或连接Windows。
- 新SDK/KDK下载需完整包清单和独立授权，未取得材料前不下载/安装。
- sync/m9-m13-sanitized只准备审核，未经新的明确确认不得推送；原私人开发祖先不发布。
