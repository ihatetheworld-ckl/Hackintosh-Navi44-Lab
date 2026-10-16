# M12 目标与证据层级

固定静态参考为 **macOS Sequoia 15.0 / Intel x86_64 / XNU 11215.1.10**。
[Apple Sequoia 兼容列表](https://support.apple.com/en-us/120282)包含 Intel Mac；
不意味着 i5-12600KF PC 获得 Apple 支持或运行认证。

本轮重新读取 Apple OSS `distribution-macOS` 的 `macos-150`：tag object
`dbaf5f8d604f45dce406bb6592608f1196533adb`，commit
`fafa0d30e9943c16e82740488dc0750c24355562`，xnu gitlink
`8d741a5de7ff4191bf97d57b9f54c2f6d4a15585`。
[固定分发树](https://github.com/apple-oss-distributions/distribution-macOS/tree/fafa0d30e9943c16e82740488dc0750c24355562)
与[固定 XNU](https://github.com/apple-oss-distributions/xnu/tree/8d741a5de7ff4191bf97d57b9f54c2f6d4a15585)
确认版本关系；pin/hash 不替代签名认证。

| 层级 | 本轮证据 | 结论 |
|---|---|---|
| A 源码存在 | 固定 XNU 源码与声明 | 可追踪参考 |
| B 头文件接口 | 真实已安装 SDK27 编译、目标15公开头文本比对 | SDK27 PASS；匹配15 SDK BLOCKED |
| C 导出参考 | IOKit/Libkern common + 对应 x86_64/arm64 表，文件哈希固定 | 13/12 个导入均存在参考 |
| D 目标二进制 ABI | 缺少版本/架构匹配的合法目标内核、KPI链接材料与类布局 | UNVERIFIED |
| E 加载调用 | 没有内核安装、加载或执行 | NOT RUN |

对象的 LC_BUILD_VERSION 标记 minos15.0、sdk27.0；最终 Kext 类型文件没有
LC_BUILD_VERSION。两个事实都不能证明 macOS15 ABI。当前开发机27、编译器21、
SDK27、目标15及未来PC实际系统是五个不同条件。arm64检查是开发侧对象检查，
没有验证 arm64e/PAC，更没有替代 Intel 执行。

全部 JSON 记录将当前SDK类型、导出参考和目标二进制状态分开。
不能通过手填偏移、混用源码头、添加 Apple API Stub 或容忍未知导入闭合目标。
