# 06 — Navi 44 (`1002:7590`) 驱动研发与本轮代码演进 (Navi 44 Driver Development)

详见 [navi44-vs-navi48-model.md](../../tahoe26/research/navi44-vs-navi48-model.md)。

## 本轮实际完成的源码演进 (`tahoe26-dev` 分支)
1. **VESA DisplayID v1.3 / v2.0 扩展块与 `2560x1440@180Hz` 高刷时序解析**：
   - 修改文件：[`src/edid.hpp`](../../development/AMDRadeonRDNA4-Navi44/src/edid.hpp)、[`src/edid.cpp`](../../development/AMDRadeonRDNA4-Navi44/src/edid.cpp)、[`core/display.hpp`](../../development/AMDRadeonRDNA4-Navi44/core/display.hpp)、[`core/display.cpp`](../../development/AMDRadeonRDNA4-Navi44/core/display.cpp)
   - 解决了 M8 遗留的经典 18-byte DTD 像素时钟上限（`655,350 kHz`）无法表达本机 `HKC2410` 等显示器 `2560x1440@180Hz`（`734,400 kHz`）的问题。
   - 保持严格的 `ExtensionPolicy` 门禁：默认 `RejectUnknown` 仍拒绝 `0x70` 块（100% 兼容 M8 回归）；显式传入 `ExtensionPolicy::AllowDisplayId` 时，严格校验 EDID 块校验和、DisplayID 区段长度、DisplayID 区段校验和、尾部零填充以及 20-byte Type I/VII 描述符几何边界，拒绝交错/3D 立体格式，且绝不离线授予 `hardwareVerified` 或 `outputAllowed`。
2. **`N44Q 1.0` (128B) → `Cobalt 192B QueryInfo` 候选投影协议**：
   - 修改文件：[`core/query_candidate.hpp`](../../development/AMDRadeonRDNA4-Navi44/core/query_candidate.hpp)、[`core/query_candidate.cpp`](../../development/AMDRadeonRDNA4-Navi44/core/query_candidate.cpp)
   - 实现了 `projectToCobaltInfo()` 与 `decodeCobaltProjection()`，将 `N44Q` 中经过验证的 `1002:7590` (`rev 0xC0`, `gfx1200`)、GC `12.0.0`、`gbAddrConfig` 与 16GB VRAM 信息显式映射到 192B `n48n_info` 兼容结构，并在 `reserved[0..7]` 写入 `'N44P'` 签名与单调 Epoch。
   - 强制离线投影下 `flags == 0`（拒绝伪造 `N48N_INFO_NATIVE_BOOT`）、`vramVisFree == 0`、`vramHiFree == 0`（拒绝离线声称可分配显存池），并拒绝任何 `gfx1201` 目标混用。
3. **测试与静态分析验证**：
   - 修改文件：[`tests/fixtures/m8_display.hpp`](../../tests/fixtures/m8_display.hpp)、[`tests/unit/m8_unit.cpp`](../../tests/unit/m8_unit.cpp)、[`tests/unit/m8_fuzz.cpp`](../../tests/unit/m8_fuzz.cpp)
   - C++ 单元测试从 `161 PASS` 提升至 **`171 PASS`**（`m65_unit=34`, `m7_unit=31`, `m8_unit=106`）；有界变异测试新增 `400` 组 DisplayID 变异与 `400` 组 Cobalt 192B 投影变异，全部通过不变量检查；Clang 23.1.3 `--analyze` 零警告。
