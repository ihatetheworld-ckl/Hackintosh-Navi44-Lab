# M11 Intel 静态参考目标

固定 **macOS Sequoia 15.0 / x86_64 / XNU 11215.1.10**，用于可追踪的历史
ABI参考与静态工程检查，不是系统安装建议或 i5-12600KF PC 的运行认证。
[Apple兼容列表](https://support.apple.com/en-us/120282)包含2019 MacBook Pro、
2018 Mac mini等Intel Mac；它没有保证目标PC受官方支持。
[macOS15 SDK说明](https://developer.apple.com/documentation/macos-release-notes/macos-15-release-notes)
将对应SDK绑定到Xcode16。

Apple OSS `distribution-macOS` 的 `macos-150` tag对象
`dbaf5f8d604f45dce406bb6592608f1196533adb`，peeled commit
`fafa0d30e9943c16e82740488dc0750c24355562`；其中xnu gitlink是
`8d741a5de7ff4191bf97d57b9f54c2f6d4a15585`，提交消息为xnu-11215.1.10。
[固定分发树](https://github.com/apple-oss-distributions/distribution-macOS/tree/fafa0d30e9943c16e82740488dc0750c24355562)、
[固定XNU](https://github.com/apple-oss-distributions/xnu/tree/8d741a5de7ff4191bf97d57b9f54c2f6d4a15585)。
公开tag未签名，pin/hash是完整性参考，不是签名认证。

本机macOS27.0.1，Xcode27/Apple Clang21；已安装SDK只有26.5/27.0，
没有15.0 SDK或15.0 x86目标内核/KPI链接输入。M11 Native使用既有27.0的真实
Kernel.framework，minos15只是编译选项。目标SDK/vtable/实际内核导出匹配 **BLOCKED**。
独立Kext文件没有LC_BUILD_VERSION；目标标签来自输入对象与命令，不能声称文件
自证15.0兼容。通用arm64对象不证明arm64e/PAC或Intel运行。

[Apple Kext弃用说明](https://developer.apple.com/support/kernel-extensions)说明
Kext/KPI的弃用与限制；[内核扩展安全模型](https://support.apple.com/en-ie/guide/security-pdf/sec8e454101b/web)
仍描述第三方Kext/AuxKC机制。导出表中存在接口，不表示当前系统允许部署。
本轮不进行任何系统策略调整、安装或加载。

现有AMDRadeonRDNA4衍生pin及Lilu/MacKernelSDK固定pin/许可继续使用
UPSTREAM_SOURCES.md记录。Lilu和MacKernelSDK没有取得，不是本次最小对象/file目标的
依赖。未来额外获取SDK/第三方组件须先确认官方来源、版本、许可证、文件SHA及用户授权。
没有下载/安装新工具或可执行依赖；在线读取的少量公开源文本只用于参考审计，
不参与include/link、不重分发为SDK。hash与来源见target-reference.json。
