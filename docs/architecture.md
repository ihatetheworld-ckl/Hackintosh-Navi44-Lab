# 当前架构：M6.5

固定 AMDRadeonRDNA4 49f7f20、Cobalt64 d6c9aed；不因本轮收尾宣称上游状态更新。

```text
allocation-free core: asicprofile / IpDiscovery / CodeObj
                     ↓
host validation: firmware / ELF metadata / descriptor / ABI / state
                     ↓
Windows CPU-only unit / probe → Python canonical comparison

macOS / IOKit / MMIO / submit adapters: future, NOT RUN
```

IpEntry 旧布局保留；新增 IpEntry64 和 initBinary 精确解析；init 保留离线 ROM 扫描。
IpDiscovery 类的内部大小改变，未来 macOS 使用者必须全部重新构建，不能假设二进制 ABI 不变。
Discovery 是调用者不可变内存的 view，调用者必须维护有效期；不读真实 ROM。
offlinevalidation.cpp 的 STL/异常属于 host 层，不可直接放入禁异常、无 libc++ 的 kext。
纯逻辑代码已真实 Windows 编译，但 macOS ABI/SDK 编译没有验证。

新增代码 BSD-3-Clause；原 LICENSE 保留。工具链各组件许可证保留；没有复制私有 Apple 框架或真实固件。
硬件 init 对所有 ASIC 恒拒绝，因此本分支也不是可直接部署的 Navi48 驱动。
