# 08 — macOS 26 Tahoe 安装资源准备方案 (Installer Preparation — Chapter 10)

> **合规提醒**：Apple macOS 软件许可协议（SLA）规定 macOS 仅许可在 Apple 品牌硬件上安装与运行。在进行黑苹果兼容性研究与部署前，请用户自行确认使用范围及合规性；本工程严禁使用任何第三方修改版/整合版黑苹果镜像。

---

## 1. 官方安装资源获取方案对比

| 维度 | 方案 A（首选推荐）：使用您的真实 Apple Mac 创建官方完整安装 U 盘 | 方案 B：在 Windows 上使用 OpenCore `macrecovery.py` 创建在线 Recovery 安装 U 盘 |
|---|---|---|
| **安装源获取方式** | 在真实 Mac 上运行 `softwareupdate --fetch-full-installer --full-installer-version 26.x` 下载官方 `Install macOS Tahoe.app`，再用 `createinstallmedia` 写入 U 盘 | 使用 OpenCore 1.0.8 自带的 `Utilities/macrecovery/macrecovery.py` 从 Apple 官方服务器下载 `BaseSystem.dmg` + `BaseSystem.chunklist` (~800MB) |
| **安装期间是否必须联网** | **否（完全离线可用）** | **是**（依赖 `LucyRTL8125Ethernet.kext` 驱动 `10EC:8125` 联网下载 14GB+ 完整系统） |
| **U 盘容量要求** | 32 GB 或以上 USB 3.0 U 盘 | 4 GB 或以上 U 盘（FAT32 分区即可） |
| **可靠性与速度** | **极高**（USB 3.0 本地高速复制，不受网络波动影响） | 中等（取决于 Apple CDN 下载速度与 RTL8125 在 Recovery 下的稳定性） |
| **恢复能力** | 完整离线恢复 + EFI 双重备份 | 需联网方可重装系统，但可直接用于引导 OpenCore |

## 2. 安装 U 盘准备流程（待 Gate B 授权后执行）

1. **在真实 Apple Mac 上执行（方案 A）**：
   - 插入您明确指定并批准擦除的 32GB+ U 盘（假设在 Mac 上为 `/dev/diskN`）。
   - 格式化为 GPT + JHFS+ (`MyVolume`)，执行：
     ```sh
     sudo "/Applications/Install macOS Tahoe.app/Contents/Resources/createinstallmedia" --volume /Volumes/MyVolume
     ```
   - 挂载该 U 盘的 `EFI` 分区，将经过校验的 `tahoe26/opencore/EFI`（补齐编译好的 `.aml` 与官方 Release 版 OpenCore 1.0.8 `.efi`/`.kext` 二进制并填入本地生成的 SMBIOS 序列号）拷入 U 盘 `EFI/BOOT` 与 `EFI/OC`。
2. **Gate B 铁律**：未经您明确确认具体 U 盘型号、容量与可擦除范围前，本 Agent 绝不在 Windows 或 Mac 上执行任何 U 盘格式化命令。
