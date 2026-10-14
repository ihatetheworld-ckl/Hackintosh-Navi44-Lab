# Discovery / Firmware：M6.5

格式依据固定 Linux discovery.h。binary v1.0..1.3/v2.0，IPDS v3/v4，单 die；其他版本拒绝。
Python 与 C++ 使用相同的合成输入，比较 header/IP/版本/base/GC_INFO/拒绝原因。
32/64 位 base 都保留；新增 ipAt64/findIp64/regByteOffset64。
旧 IpEntry 为 uint32_t，只有值可表示才返回；高位不会静默截断。
base 是寄存器 segment 的 dword 基址，byte offset 转换检查乘法/加法，不等于 PCI BAR/物理地址。

FirmwareRequirements 已有 C++ 模型，核对 ASIC/GC、所需 IP、拓扑描述缺失；仍是 advisory 组件清单。
GC_INFO SE/RB、非GC IP 版本和固件 payload 均来自合成输入，不代表本机。
Common header 仅 v1.0；大小、payload、major/minor、允许的组件声明检查已测试。
common header 不编码完整 revision/组件身份，sidecar 声明不是实际组件内容认证。
非零 CRC 明确 firmware_crc_unverified；未猜测 AMD CRC 覆盖范围或伪报签名验证。
PSP v2/package/真实加载顺序等尚未支持。没有下载、解析真实 GPU 固件或上传。
