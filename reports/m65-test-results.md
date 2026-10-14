# M6.5 实际测试结果

最终记录：[results.json](m65/results.json)，时间2026-10-14T00:37:40.503321+08:00。

| 类别 | 真正执行结果 | 说明 |
|---|---|---|
| 原Python基线 | 56 PASS / 2 SKIP / 0 FAIL | 58项，其中4个PASS为静态检查 |
| 新Python回归 | 11 PASS / 0 FAIL | metadata/descriptor/组件/范围 |
| Python函数行为合计 | 63 PASS | 不计4个静态检查 |
| C++单元 | 34 PASS / 0 FAIL | 真正编译的函数行为 |
| 共享差分 | 537输入零差异 | 接受/输出/拒绝原因 |
| 受控变异 | 2400输入零差异/无崩溃 | seed759065，非coverage-guided |
| ASan/UBSan | 34unit + 2937输入PASS | 与普通输入重跑，不能累计为独立功能数量 |
| 检测器canary | 2种预期故障被捕获 | 非零退出是预期 |
| 静态分析 | 3个source零warning | 不是函数行为测试 |
| 真Navi44/真shader | SKIP | fixture缺失/无AMDGPU backend |
| GPU/Kext | NOT RUN | 未授权/无macOS构建 |

不把静态检查、重复sanitizer运行或多个截断点混成“驱动功能PASS总数”。
LeakSanitizer没有验证，detect_leaks=0；有限输入没有证明全覆盖。

## C++行为测试清单

| 测试 | 结果 |
|---|---|
| navi44_identity | PASS |
| navi48_7550 | PASS |
| navi48_7551 | PASS |
| unknown_device | PASS |
| revision_unverified | PASS |
| topology_unknown | PASS |
| hardware_permanently_disabled | PASS |
| discovery_valid | PASS |
| legacy_entry | PASS |
| gc_info | PASS |
| manifest_missing_ip | PASS |
| manifest_wrong_gc | PASS |
| discovery_64 | PASS |
| high_bits_preserved | PASS |
| legacy_narrow_rejected | PASS |
| 64bit_byte_offset | PASS |
| 32bit_offset_rejected | PASS |
| address_overflow_rejected | PASS |
| all_truncations | PASS |
| failure_clears_state | PASS |
| bad_checksum | PASS |
| firmware_header | PASS |
| firmware_wrong_ip | PASS |
| firmware_unknown_component | PASS |
| firmware_crc_fail_closed | PASS |
| elf_bad_header | PASS |
| elf_unknown_target | PASS |
| old_codeobj_rejects | PASS |
| state_cannot_jump | PASS |
| failed_terminal | PASS |
| offline_sequence | PASS |
| ready_terminal | PASS |
| abi_navi44 | PASS |
| abi_capability_rejected | PASS |
