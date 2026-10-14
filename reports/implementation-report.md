# 实际开发交付报告

## 1. 进度

M0已创建独立目录、克隆并固定源码；M1已实现profile；M2已实现host parser/firmware模型及C++加固；M3已参数化C++target并实现host ELF校验；M4已加门禁并实际运行CPU测试；M5已实现模拟ABI；M6已生成补丁、日志和报告。
这些均为离线软件成果。C++及完整Kext未编译，硬件部分未完成。

## 2. 环境

目录：`D:\CodexWorkSpace\黑苹果研究\Hackintosh-Navi44-Lab`。
Python3.12.13；Git现有工具；没有可用C++/CMake/Apple SDK。固定来源见 [provenance.json](provenance.json)。
首个sandbox网络请求失败，网络授权后仅clone/text下载；没有管理员权限请求。未安装工具，未改global PATH/Git。

## 3. 开发副本修改

- `Makefile`
- `src/asicprofile.hpp`
- `src/offlinefirmware.hpp`
- `src/plugin.cpp`
- `src/device.cpp`
- `src/codeobj.hpp`
- `src/codeobj.cpp`
- `src/ipdiscovery.hpp`
- `src/ipdiscovery.cpp`
- `host/navi44.py`

`tests/test_offline.py`、`tests/fixtures/synthetic.py`、`tests/unit/host_tests.cpp`、`run_offline.py`、`build_offline.ps1`、`CMakeLists.txt`及docs/reports为新增交付。
上游参考快照不修改。开发副本包含原LICENSE，原危险工具未运行。

## 4. 原型实现

PCI/ASIC/revision/target描述；未知能力关闭；profile与绑定分离；Discovery版本/checksum/边界；firmware需求与结构校验；ELF目标与metadata子集；失败状态；N44I模拟协议。
详见docs。本原型没有硬件后端，不是可加载驱动。

## 5. 实际测试

56 PASS、0 FAIL、2 SKIP，合计58。见 [测试报告](test-results.md)。
C++/Kext/真实GPU为NOT RUN，不能用Python PASS替代。

## 6. 质量与限制

当前C++改动未经编译；parser/firmware/metadata支持范围有限；真实fixture缺失；需进一步交叉实现回归、fuzz和安全审计。
所有合成拓扑与非GC版本明确不是本机参数；不公开未验证硬件功能。

## 7. 功能等级

| 功能 | 实际状态 |
|---|---|
| PCI/Profile | Python离线PASS，C++源码完成未编译 |
| Discovery | Python32/64离线PASS；C++加固未编译，64明确拒绝 |
| Firmware | 合成manifest/结构PASS，真实固件未验证 |
| gfx1200 | 离线目标校验PASS，真正shader未验证 |
| 基础显示 | NOT RUN，未部署 |
| GPU提交/Vulkan/Metal/WindowServer | NOT RUN，未接入 |

## 8. 后续

先补现有合法C++工具链与纯fixture测试，再考虑完善固件/metadata/64位接口。显示与GPU实机需另行授权，不能由本报告自动进入。

代码与补丁：[navi44-offline-prototype.patch](../patches/navi44-offline-prototype.patch)。
