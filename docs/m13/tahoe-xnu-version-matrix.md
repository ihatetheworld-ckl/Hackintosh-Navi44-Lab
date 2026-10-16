# Tahoe 多版本参考矩阵

2026-10-16只读核对Apple官方资料与分发tag/gitlink；原始pin见version-matrix.json。

| 系统版本 | 固定公开XNU | 本机SDK/头 | 目标二进制/KDK | 选择 |
|---|---|---|---|---|
| 26.0 | 12377.1.9 / f6217f891ac0bb64f3d375211650a4c1ff8ca1ea | 未发现26.0 | 未取得 | 历史对照，不拿26.5头冒充26.0 |
| 26.4 | 12377.101.15 / 5c306bec31e314fa4d8bbdafb2f6f5a6b7e7b291 | 未发现26.4 | 未取得 | 源码对照 |
| 26.5 | 12377.121.6 / ac9718fb1af618d5ce8678d0dc6e8a58f252216f | CLT26.5含Kernel.framework | 未取得 | 本轮静态基线 |
| 26.5.1/26.5.2及26.6.x | Apple更新列表存在，具体XNU/build未核验 | 无独立对应SDK | 未取得 | 不假设ABI相同 |
| 26.7.1 | Apple更新列表当前列出；本次查询的OSS macos-26前缀tag仅到265 | 未发现 | 未取得 | 不冒充已验证或最终安装目标 |

[Apple更新列表](https://support.apple.com/en-us/122868)、
[Apple SDK/Xcode对应表](https://developer.apple.com/xcode/system-requirements/)。
Darwin25是目标系列；实际内核banner/build未取得，不把SDK25F70或XNU源码版本
当成已经读到目标机器的Darwin版本。SDK26.5元数据25F70是SDK来源证据。
Xcode27/Clang21配合SDK26.5的结果是实际编译证据，不是Apple对该组合的运行认证。

若推进二进制核验：来源为[Apple More Downloads](https://developer.apple.com/download/more/)
对应26.5且匹配准确build的KDK；适用Apple随包许可，用途只读KPI/符号/类布局。
精确包名、下载大小、SHA及目标build尚未取得，不能虚构；系统安装不在计划内。
需先形成包清单再独立批准下载，且只能在Lab中离线处理。已询问是否有现成合法材料，
当前验证保持BLOCKED，不下载SDK/KDK、不执行pkg或安装器。
