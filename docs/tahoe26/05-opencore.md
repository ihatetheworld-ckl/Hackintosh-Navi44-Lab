# 05 — OpenCore 1.0.8 候选工程说明 (OpenCore Configuration)

- **候选配置文件**：[`tahoe26/opencore/EFI/OC/config.plist`](../../tahoe26/opencore/EFI/OC/config.plist)
- **定制 USB 映射**：[`tahoe26/opencore/EFI/OC/Kexts/UTBMap.kext/Contents/Info.plist`](../../tahoe26/opencore/EFI/OC/Kexts/UTBMap.kext/Contents/Info.plist)
- **离线校验脚本**：[`tahoe26/scripts/validate_opencore_candidate.py`](../../tahoe26/scripts/validate_opencore_candidate.py)
- **校验结果**：`12 / 12 PASS` (`tahoe26/tests/host/opencore-validation-report.json`)

## 关键设计决策
1. **SMBIOS 选择 `MacPro7,1`**：
   - 原生支持无核显（dGPU-only）架构，不会触发 Intel iGPU Framebuffer 查找，也不会因内存插槽拓扑触发 `AppleSMBIOS` 内存警告（配合 `CustomMemory = false`）。
   - 序列号字段使用本地占位符 `PLACEHOLDER_LOCAL_SN`，遵守不提交公开共享序列号的安全要求。
2. **SMBIOS 与启动变量隔离**：
   - `Kernel -> Quirks -> CustomSMBIOSGuid = true` + `PlatformInfo -> UpdateSMBIOSMode = Create`：彻底隔离 SMBIOS，不污染 Windows。
   - `UEFI -> Quirks -> RequestBootVarRouting = true` + `Misc -> Boot -> LauncherOption = Full`：不修改 Windows Boot Manager。
3. **DeviceProperties 精确匹配本机三层 PCIe 桥**：
   - RX 9060 XT：`PciRoot(0x0)/Pci(0x1,0x0)/Pci(0x0,0x0)/Pci(0x0,0x0)/Pci(0x0,0x0)`
   - Intel 256GB 目标盘：`PciRoot(0x0)/Pci(0x1C,0x4)/Pci(0x0,0x0)`
   - Realtek RTL8125 有线网卡：`PciRoot(0x0)/Pci(0x1D,0x0)/Pci(0x0,0x0)`
