# 合法 SDK 与 KDK 缺口

本机现有 Xcode27 / SDK26.5、27.0；没有15.0 SDK，未取得目标15 x86_64
内核或匹配KDK。本轮只读取少量公开源文本作参考，不参与 include/link，未安装依赖。

[Apple Xcode表](https://developer.apple.com/xcode/system-requirements)及
[Xcode16发布说明](https://developer.apple.com/documentation/xcode-release-notes/xcode-16-release-notes)
确认 Xcode16 携带 macOS15 SDK。Xcode16官方Host范围为 Sonoma14.5–Sequoia15.x；
不能假设旧IDE能在当前27系统启动。未来即使只在Lab内提取合法SDK，也需独立授权、
许可核查及工具链兼容验证，不能更改 xcode-select 或覆盖当前安装。

| 可选材料 | 官方来源/版本 | 许可与用途 | 体积/哈希与状态 |
|---|---|---|---|
| Xcode16 / SDK15.0 | [Apple More Downloads](https://developer.apple.com/download/more/) 的 Xcode16 正式包 | Apple Xcode/SDK协议；匹配公开Kernel.framework声明 | 下载规划预算10–15GB，非实测包大小；完整包/展开大小与SHA-256需授权后确认。BLOCKED |
| 目标15.0 x86_64 KDK | 同一官方下载入口，须固定真实15.0系统build再选对应KDK | Apple随包许可；只读取目标内核/符号做离线比对，不能执行安装器 | 规划预算1–3GB，非实测；版本build、包大小、SHA未取得。BLOCKED |
| 已固定公开XNU | 上文固定Apple OSS commit | 文件内Apple公开源码许可；源码/导出参考 | 小量文本已读取；不是匹配SDK或二进制 |
| Lilu/MacKernelSDK | UPSTREAM_SOURCES.md中的固定pin和许可证 | 后续完整工程的可选依赖，不解决目标二进制缺口 | 本轮未获取，未经授权不下载；MacKernelSDK不等于官方SDK15 |

预算仅用于决定是否另行授权，没有认证下载包事实。Apple下载页面可能要求登录及
接受协议，不登录、不自动安装、不猜SHA。获取前应复核官方文件名、build、版本、
许可、下载/展开体积和所有写入位置；不能在本轮主动执行上述步骤。
[Apple KDK文档](https://developer.apple.com/documentation/apple-silicon/debugging-a-custom-kernel-extension)
要求选择对应待调试macOS版本的KDK；本项目只考虑其静态材料，调试/加载不在授权内。

补齐SDK仅解决声明及编译目标。还须校验真实目标二进制符号、KPI来源、IOService/
OSObject/OSMetaClass布局与vtable；实际加载仍是另一项未授权验证。
