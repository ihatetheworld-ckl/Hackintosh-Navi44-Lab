# 非部署型 Kernel Partial Link

本轮使用已安装的 Apple `ld-27037.1`，分别对x86_64和arm64执行真实`ld -r`。
每架构14个对象：九个原Core/解析单元、lifecycle、darwin_native、darwin_snapshot、
M10契约探针、M8契约探针。排除device/plugin/fwblobs及硬件程序。

一般形式如下，具体实际argv见M10 commands与本地原始日志：

```text
ld -r -arch <x86_64|arm64> -platform_version macos 13.0 27.0 \
  -o build/m10/native-<arch>/n44-offline-partial.o <explicit object allowlist>
```

结果必须是单架构MH_OBJECT。脚本拒绝错误CPU、非object、dylib加载/运行入口命令、
全局初始化与异常表；再检查nm、otool load commands/relocations、file、lipo。
两个CPU各20个内部依赖实际闭合；Kernel外部导入仍然保留。

这是可继续静态链接/分析的Relocatable Object，不是可加载模块或可安装Bundle。
没有Kext entry/Info.plist/设备匹配表、签名、部署脚本或执行动作。
Full Kext Link、Kernel Runtime、GPU Runtime全为NOT RUN。

13.0部署标记与27.0 SDK是本次编译参数，不代表macOS13实机兼容或目标内核验证。
arm64是通用对象目标，不是arm64e/PAC内核验证。
未知链接器问题应保存错误并停止该目标，不通过伪造导出、stub或系统修改绕过。
