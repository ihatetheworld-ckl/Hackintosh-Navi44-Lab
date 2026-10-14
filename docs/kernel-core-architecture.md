# M7 Core / Host / Darwin 架构

## 实际分层

~~~mermaid
flowchart LR
    W[Windows CPU tests / Python reference] --> H[Host compatibility / fixed mock]
    H --> C[Core: views, Result, bounded metadata, package, ABI]
    C --> P[Existing ASIC / Discovery / CodeObj pure logic]
    F[Future genuine Darwin build] --> D[Darwin native allocator/log/error draft]
    D --> I[Platform contract]
    I --> C
~~~

Core 包含 core/validation.hpp/.cpp、model.hpp、device_info.hpp/.cpp，以及继续复用的
src/asicprofile.hpp、ipdiscovery.cpp/.hpp、codeobj.cpp/.hpp。没有创建第二套 Discovery 解析器。
现有固件需求模型和状态机已移入 Core；旧 Offline::Session / State / FirmwareRequirement 是同一类型的别名。

Host 包含 host/validation_adapter.hpp、platform_mock.hpp、Python 参考、probe 和 tests。
src/offlinevalidation.cpp 是旧 API 的兼容转发层；其 MetadataBuffer 有较大的 Host 栈缓冲，未来内核不链接该文件。
STL/异常保留在 Host probe 与测试中，Core 源码不使用这些功能。

Platform contract 提供显式 MemoryOps / LogOps / SnapshotOps 与 Lease。
SnapshotKind 仅描述 CPU 文件输入，没有 BAR、MMIO、ROM、GPU queue 或 DMA API。
Darwin contract 可由 Host Mock 编译；darwin_native.cpp/.hpp 仅供真实 Apple Kernel SDK 的未来构建。

## 所有权与失败规则

- View 借用不可变 CPU 缓冲；调用方保证地址可访问、真实长度正确，并在整个解析过程保持存活。
- Scratch 使用调用方提供的 Node 数组。Core 不隐式分配，也不拥有输入。
- metadata 字符串借用输入；elf() 不返回节点或字符串，失败令 scratch.used=0。
- Package 的 payload View 会返回给调用方，生命周期不得超过原始输入；不是复制或固件许可。
- Result.detail 为内部静态诊断 token，offset 是输入偏移。并非任意用户字符串或硬件地址。
- Discovery 对象保存借用输入及条目偏移，必须与其源缓冲共同存活；旧对象布局不可视为稳定 ABI。
- Lease 禁止复制，校验 alignment，重复释放为空操作，释放后自身 view 清空。
  已复制出去的 View 不会自动失效；调用方不得在 close 后使用旧副本。
- Manifest / ABI / Package 验证失败会清空输出。OfflineReady 只代表离线流程完成。
- 输入完整性、CRC、PSP 签名和设备执行授权是不同条件。当前 capabilities 恒为 0，hardwareAllowed 恒 false。

## 限额

Host metadata scratch 512 节点；递归深度上限 16；容器计数上限 4096，节点索引小于 UINT16_MAX。
ELF 当前 PT_LOAD 虚拟范围上限为 16 MiB；这是既有实验性策略，并非通用 ROCm loader。
PSP package 最多 12 个已知类型；未知版本、重复类型、重叠、未支持 aux 和非零未验证 CRC 拒绝。
没有 runtime ABI 直接序列化 C++ 对象。N44I 使用显式 little-endian 字节读写。
