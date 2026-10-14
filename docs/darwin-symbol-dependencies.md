# Darwin 符号依赖：M10

本轮真实 Apple Clang/SDK 编译，Apple ld 部分链接。机器可读条目见
`reports/m10/symbol-audit.json`、`native-object-results.json` 和 `export-reference.json`。
对应公开 XNU 固定参考为
[`f6217f891ac0bb64f3d375211650a4c1ff8ca1ea`](https://github.com/apple-oss-distributions/xnu/tree/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea)。
这不是已核实与本机/目标 Intel 内核完全匹配的源码版本。

| 分类 | 含义与本轮结果 |
|---|---|
| INTERNAL_RESOLVED | 每架构20个跨对象符号，由同一明确源码集实际提供；部分链接后不再 undefined |
| EXPECTED_KERNEL_IMPORT | x86_64剩7个、arm64剩6个，公开导出参考有对应条目 |
| HOST_ONLY_DEPENDENCY | 本轮正常内核集0；真实 Host SDK `_puts` 负样本实际被策略拒绝 |
| UNSUPPORTED_DEPENDENCY | 本轮正常对象未出现；异常/RTTI/Host runtime/stack-check泄漏会停止审查 |
| UNKNOWN | 最终两架构均0；首次遗漏架构导出表时Buffer工厂曾为UNKNOWN，补齐真实来源后重新审查 |
| REQUIRES_REAL_KERNEL_LINK | 所有外部导入都具有该标记，即使属于EXPECTED也未验证目标内核最终链接 |

实际剩余符号：`_IOMallocAligned`、`_IOFreeAligned`、`_IOLog`、`_memcpy`、
`__ZN6OSData9withBytesEPKvj`、`__ZN24IOBufferMemoryDescriptor9withBytesEPKvmjb`；
x86_64额外有`___bzero`。没有为它们创建假的实现。

`config/IOKit.exports` 中 IOMallocAligned 还有外部入口别名，
`config/Libkern.exports` 提供 memcpy/__bzero，Buffer工厂在对应架构的
`IOKit.x86_64.exports`/`IOKit.arm64.exports`，不能仅查公共列表就误判其缺失。
公开参考原文只保留本地；公开报告保存来源、pin、文件SHA及实际用到的条目。

每个对象实际执行 nm undefined/defined，结合定义提供方和架构参考分类。
使用真实对象验证错误CPU拒绝，真实stdio头编译负样本验证Host导入拒绝。
检查不支持 C++异常、RTTI、全局new/delete、用户态stdio/heap/pthread依赖。
普通内核导入不作为编译失败；未知导入不会冒充已解析。

ABI审查覆盖同一SDK、C++17、KERNEL/KERNEL_EXTENSION、fapple-kext、无异常/RTTI、
无stack protector、x86 no-red-zone、目标/布局断言、Mach-O和DWARF合法性。
它不能验证目标内核vtable、OSObject二进制布局、arm64e/PAC或真正调用结果。
