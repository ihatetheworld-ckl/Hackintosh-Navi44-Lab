# 11 — 真机硬件与 Navi 44 渐进式实验计划 (Hardware & GPU Test Plans — Chapter 12 & 13)

> **安全门禁**：所有涉及加载 `AMDRadeonRDNA4.kext`、访问 GPU BAR/MMIO、读取本机 VBIOS/IP Discovery 或提交命令的实验，均属于 **Gate D**，必须在 macOS 26 基础系统安装完毕且您单独批准 Gate D 后方可逐项执行。

---

## 渐进式 GPU 真机实验梯度 (Experiments 1..9)

| 实验编号 | 实验名称 | 执行内容与验证指标 | 超时与故障停止条件 | 回退机制 |
|---|---|---|---|---|
| **Exp 1** | **PCI / IORegistry 设备识别** | 不加载任何自定义 GPU Kext，在 macOS 26 下运行 `ioreg -l -p IODeviceTree` 与 `system_profiler SPDisplaysDataType`，验证 `1002:7590` (`rev 0xC0`, Subsys `1458:2438`) 在 `PC00.PEG0.PEGP.SWUS.SWDS` 下的枚举 | 只读命令，5 秒超时 | 无需回退（零内核改动） |
| **Exp 2** | **只读采集本卡 Discovery / AtomBIOS 并在 CPU Core 离线验证** | 在获批后提取本卡静态 Discovery / ROM 镜像，先用本仓库 `navi44_m8_tests` 验证 `GC 12.0.0`、`DCN 4.0.1`、`ConnectorList` 与 `GB_ADDR_CONFIG` 真实值 | 若解析返回 `Error::Format` / `Mismatch`，立即停止，不进入 Kext 加载 | 纯用户态文件解析，零系统风险 |
| **Exp 3** | **安全 Probe-Only Kext 匹配** | 加载仅开启只读 Probe 模式（`hardwareInitializationAllowed() == false`、不接管 GOP、不写 MMIO）的 `AMDRadeonRDNA4-Navi44.kext`，检查 `kmutil showloaded` 与 `log show` 中的 `N44Core` 诊断输出 | 若发生 Panic 或卡死，重启在 OpenCore 菜单按空格禁用 Kext 或用备份 U 盘启动 | OpenCore U 盘一键无 Kext 启动 |
| **Exp 4** | **GOP Framebuffer 接管与 EDID/DisplayID 核验** | 验证 HUBP0/OTG0 当前 GOP 扫描表面地址 (`plane_mc`)、分辨率与 `HKC2410` 显示器 EDID/DisplayID 模式表 | 若黑屏超过 15 秒，触发 `N48N_SCANST_RESTORING` 看门狗恢复原 `console_mc` | 自动恢复 `console_mc` 或长按电源重启回 GOP 模式 |
| **Exp 5** | **显示模式切换与高刷试验 (`N48N_SEL_MODE_TRIAL`)** | 使用带定时自动回退（15 秒 dwell）的 `MODE_TRIAL` 测试 DP/HDMI 模式与刷新率切换 | 定时到期或监测到 OTG underflow 立即自动回退至初始 GOP 时序 | 硬件/内核定时器自动回退 |
| **Exp 6** | **VRAM / BO / GART 页表与 Fence 验证** | 验证 16GB VRAM 可见池 (`vramVisTotal`)、BO 创建/释放与 GPU VM 页表映射 | 单次分配上限 64 MiB，客户端总上限受控 | 进程退出自动 unmap + 释放页表 |
| **Exp 7** | **GFX12 命令提交与 Compute 验证** | 提交最小 PM4/GFX12 NOP 与简单计算 Shader，验证 `seq_emitted == seq_retired` | `N48N_WAIT_CAP_NS` (2 秒) 超时立即锁存 `N48N_INFO_HUNG` 并拒绝后续提交 | HUNG 锁存防死锁 |
| **Exp 8** | **Mesa RADV Vulkan (`vkprobe`) 验证** | 通过更新了 `gfx1200` 支持与 `CobaltQueryProjection` 的 RADV Darwin winsys 运行 `vkprobe` 离屏渲染与扫描输出 | 用户态进程级隔离，60 秒超时 | 终止用户态进程并释放 Scanout 槽 |
| **Exp 9** | **Cobalt64 Metal (`navi48-metal=1`) 与稳定性验证** | 仅在 Exp 1–8 全部 `VERIFIED_REAL_HARDWARE` 后，按需发布 Metal Nub (`N48N_SEL_METAL_NUB_PUBLISH`) 测试 Metal 设备创建 | 绝不在开机时默认发布 Metal Nub（坚持 on-demand publish 防止开机直接崩溃进入死循环） | 调用 `N48N_SEL_METAL_NUB_WITHDRAW` 或重启自动恢复无 Metal 安全状态 |
