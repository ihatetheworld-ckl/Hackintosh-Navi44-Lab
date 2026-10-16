# Kernel ABI26 与独立拒绝

当前SDK26.5实际对象仍有x86_64 13、arm64 12个预期导入；内部依赖全部解析。
包括allocator/log、IORecursiveLock三函数、OSData/Buffer工厂、IOService vtable、
memcpy、ml上下文函数以及x86的实际___bzero。完整拼写、调用源、参数宽度和
架构对应源码export项见kpi-details.json/symbol-audit.json。

| 证据 | 状态 |
|---|---|
| SOURCE_DECLARED | 已读取IOLib、OSData、Buffer、锁、machine routines及类头；未取得的直接声明单列UNVERIFIED |
| SDK_DECLARED | 真正26.5头及static_assert；编译器生成的___bzero不假称同名普通声明 |
| REFERENCE_EXPORTED | 26.5 common + 相应架构IOKit/Libkern导出表核对PASS |
| TARGET_BINARY_VERIFIED / TARGET_ABI_VERIFIED | UNVERIFIED；KDK/目标二进制未取得 |
| 正常UNKNOWN/UNSUPPORTED/Host/EH/RTTI导入 | 0 |

原M12对象审计器继续作为独立格式/符号层，M13新增版本、依赖路径、Source SHA及
类型边界。19类负样本均REJECTED：原10类加SDK27选择/头/对象、旧部署目标、
旧参考pin、参考内容变异、错误格式、实际API类型不匹配、禁止初始化路径。
实际类型错误使用真实IOLog声明配错误static_assert，编译器真实exit1；不伪造API。
puts隔离负Kext仍可被ld接受exit0，独立策略拒绝；没有放宽undefined规则获取PASS。

22对象/架构、ld-r、x86 MH_KEXT_BUNDLE构造PASS不等于TARGET_ABI_CLOSURE。
最终文件保留内核导入且无LC_BUILD_VERSION；输入对象minos26.5/sdk26.5只证明
标签与配置一致。Bundle/Sign/Install/Load及Kernel/GPU Runtime均NOT RUN。
