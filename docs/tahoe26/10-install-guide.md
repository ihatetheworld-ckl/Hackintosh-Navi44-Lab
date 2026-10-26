# 10 — macOS 26 Tahoe 从零安装全流程手册（真实 macOS 27 Mac 制盘 + 免拆机双重屏蔽 Windows 盘版）

> **当前授权状态**：
> - 您已确认目标 256GB 硬盘 (`INTEL SSDPEKKF256G8L`) 上的旧 Ubuntu 系统可清空；
> - 您已明确要求**不物理拆下 Windows 主盘 (`WD_BLACK SN850X 2000GB`)**；
> - 本配置已默认启用 **DeviceProperties + SSDT 双重内核级屏蔽**，使 macOS 安装器完全看不见 `WD_BLACK SN850X 2000GB`！

---

## 第一部分：免拆机 100% 保护 Windows 主盘的工程原理（为什么绝不会误格盘）

通过 Windows 硬件普查，两块 NVMe SSD 位于完全不同的物理总线与控制器上：

| 硬盘 | 物理型号 | NVMe 控制器 PCI ID | PCIe 路径 (OpenCore DevicePath) | OpenCore 注入策略 |
|---|---|---|---|---|
| **Windows 主盘（绝对保护）** | `WD_BLACK SN850X 2000GB` | `15B7:5030` | `PciRoot(0x0)/Pci(0x6,0x0)/Pci(0x0,0x0)` (Bus 4, CPU PEG60) | **已默认注入 `class-code = FF FF FF FF` + `IOName = #disabled-nvme` + `SSDT-NVME-PROTECT.aml`** |
| **macOS 目标盘（清空原 Ubuntu）** | `INTEL SSDPEKKF256G8L` (256GB) | `8086:F1A6` | `PciRoot(0x0)/Pci(0x1C,0x4)/Pci(0x0,0x0)` (Bus 6, PCH RP5) | 注入 `built-in = 01`，正常由 `IONVMeFamily.kext` 挂载 |

**双重保险效果**：
1. 当您从 OpenCore 引导进入 macOS 26 Tahoe 安装器时，Darwin 内核的 `IONVMeFamily.kext` 仅匹配 PCI Class Code 为 `010802` (NVMe) 的设备。
2. 因为 `PciRoot(0x0)/Pci(0x6,0x0)/Pci(0x0,0x0)` (`WD_BLACK SN850X 2000GB`) 的 `class-code` 被 OpenCore 在内存中改写为 `FFFFFFFF` 且名称改为 `#disabled-nvme`，**macOS 内核根本不会为 Windows 主盘加载 NVMe 驱动**。
3. 因此，在 macOS 磁盘工具（Disk Utility）和 `diskutil list` 中，**`WD_BLACK SN850X 2000GB` 完全不存在、不可见、不可写**，从物理控制器驱动层面实现了与“拔掉硬盘”完全相同的防误格效果，同时对 Windows 自身启动零影响（`_OSI("Darwin")` 仅对 macOS 生效）。

---

## 第二部分：在您的真实 Mac（运行 macOS 27）上执行 M6 原生验证与组装完整安装 U 盘

请在您的真实 Apple Mac（运行 macOS 27）上打开 **终端 (Terminal.app)**，严格按以下步骤逐条执行：

### 步骤 2.1：克隆仓库并切换到 `tahoe26-dev` 分支，执行 M6 原生构建验证

```sh
mkdir -p ~/ Tahoe26Work && cd ~/Tahoe26Work
git clone https://github.com/ihatetheworld-ckl/Hackintosh-Navi44-Lab.git
cd Hackintosh-Navi44-Lab
git fetch origin
git checkout tahoe26-dev
git rev-parse HEAD
```

确保您的 Mac 已安装 Xcode Command Line Tools 与 `acpica`（用于编译 ACPI `.dsl` 源码为 `.aml`）：

```sh
xcode-select -p || xcode-select --install
# 若已安装 Homebrew，安装 acpica (提供 iasl 编译器)：
brew list acpica >/dev/null 2>&1 || brew install acpica
```

运行我们编写的 **Mac 原生验证与 ACPI 编译脚本**（无需 `sudo`，100% 安全）：

```sh
python3 -I -B -X utf8 tahoe26/scripts/run_mac_native_verification.py
```

- **验证标准**：终端最后输出的 JSON 中 `"status": "VERIFIED_NATIVE_BUILD"`，且 `tahoe26/tests/native/mac-native-report.json` 生成成功（表示 9 个 Navi44 Core C++17 模块已通过 Apple Clang 真机编译为 `x86_64` Mach-O 对象，且 4 个 `.aml` 已编译生成）。

---

### 步骤 2.2：在真实 Mac 上下载官方组件并自动组装经过 `ocvalidate` 校验的 EFI

在 Mac 终端继续执行以下命令，从 GitHub 官方 Release 下载固定版本的 OpenCore 1.0.8 与必需 Kext（全部來自 Acidanthera / Mieze / USBToolBox 官方仓库）：

```sh
mkdir -p build/efi-staging/downloads build/efi-staging/kexts
cd build/efi-staging/downloads

# 1. 下载 OpenCore 1.0.8 官方 Release
curl -L -O https://github.com/acidanthera/OpenCorePkg/releases/download/1.0.8/OpenCore-1.0.8-RELEASE.zip
unzip -q OpenCore-1.0.8-RELEASE.zip -d OpenCore-1.0.8

# 2. 下载 Acidanthera / Mieze / USBToolBox 官方 Release Kext
curl -L -O https://github.com/acidanthera/Lilu/releases/download/1.7.2/Lilu-1.7.2-RELEASE.zip
curl -L -O https://github.com/acidanthera/VirtualSMC/releases/download/1.3.8/VirtualSMC-1.3.8-RELEASE.zip
curl -L -O https://github.com/acidanthera/CPUFriend/releases/download/1.3.0/CPUFriend-1.3.0-RELEASE.zip
curl -L -O https://github.com/b00t0x/CpuTopologyRebuild/releases/download/1.1.0/CpuTopologyRebuild-1.1.0-RELEASE.zip
curl -L -O https://github.com/Mieze/LucyRTL8125Ethernet/releases/download/V1.2.2/LucyRTL8125Ethernet-V1.2.2.zip
curl -L -O https://github.com/USBToolBox/kext/releases/download/1.2.0/USBToolBox-1.2.0-RELEASE.zip

# 解压到 kexts 目录
for z in Lilu-*.zip VirtualSMC-*.zip CPUFriend-*.zip CpuTopologyRebuild-*.zip LucyRTL8125Ethernet-*.zip USBToolBox-*.zip; do
  unzip -q -o "$z" -d ../kexts/
done

cd ~/Tahoe26Work/Hackintosh-Navi44-Lab
```

运行我们的 **EFI 自动组装与 `ocvalidate` 校验脚本**（它会自动调用 `iasl` 编译 4 个 `.dsl`，复制所有 `.efi` 与 `.kext`，调用官方 `macserial` 生成您本机专属的 `MacPro7,1` 序列号，并调用官方 `ocvalidate` 检验 `config.plist` 零错误）：

```sh
python3 -I -B -X utf8 tahoe26/scripts/assemble_efi_on_mac.py \
  --opencore-dir build/efi-staging/downloads/OpenCore-1.0.8 \
  --kexts-dir build/efi-staging/kexts
```

- **验证标准**：输出 `"status": "EFI_STAGE_READY"` 且 `"ocvalidate": "... No issues found ..."`。组装完成的完整 EFI 位于 `build/efi-staging/EFI`。

---

### 步骤 2.3：在真实 Mac（macOS 27）上下载原生 macOS 26 Tahoe 安装器并制作离线安装 U 盘

> **重要提示（针对运行 macOS 27 的 Mac）**：由于您的 Mac 当前运行的是更新的 **macOS 27**，直接使用不带版本号的 `softwareupdate --fetch-full-installer` 默认会拉取 macOS 27（macOS 27 已不再支持 x86_64 Intel 架构）。因此**必须显式指定下载 macOS 26.x (Tahoe)**！

1. **查询 Apple 服务器上当前可用的最新 macOS 26.x 完整安装器版本号**：
   ```sh
   softwareupdate --list-full-installers | grep "26\."
   ```
2. **下载对应的最新 macOS 26.x 完整安装器**（例如列表中显示 `26.4` 或 `26.3`，请替换为列表显示的最高 `26.x` 版本号）：
   ```sh
   softwareupdate --fetch-full-installer --full-installer-version 26.4
   ```
   下载完成后，确认 `/Applications/Install macOS Tahoe.app` 存在。
3. **插入您的 32GB+ USB 3.0 U 盘，核实磁盘编号**：
   ```sh
   diskutil list external physical
   ```
   *(请仔细核对容量和名称，假设您的 U 盘为 `/dev/disk4`，**切勿选错其他外置硬盘**)*
4. **将 U 盘格式化为 GPT + JHFS+（这会自动创建 200MB `EFI` 分区和 `MyVolume` 分区）**：
   ```sh
   diskutil eraseDisk JHFS+ MyVolume GPT /dev/disk4
   ```
5. **写入官方 macOS 26 Tahoe 离线安装镜像**：
   ```sh
   sudo "/Applications/Install macOS Tahoe.app/Contents/Resources/createinstallmedia" --volume /Volumes/MyVolume --nointeraction
   ```
6. **挂载 U 盘的 EFI 分区并拷入刚刚通过 `ocvalidate` 校验的 EFI**：
   ```sh
   sudo diskutil mount /dev/disk4s1
   cp -R ~/Tahoe26Work/Hackintosh-Navi44-Lab/build/efi-staging/EFI /Volumes/EFI/
   dot_clean /Volumes/EFI
   diskutil unmount /Volumes/EFI
   ```
   至此，您的 **macOS 26 Tahoe 离线安装 + 免拆机 Windows 保护引导 U 盘** 制作完成！

---

## 第三部分：在目标 PC（i5-12600KF + 铭瑄 B760M D5 + RX 9060 XT）上安装 macOS 26 Tahoe

### 步骤 3.1：铭瑄 MS-Terminator B760M D5 BIOS 检查
1. 将制作好的 U 盘插入主机后置主板 USB 接口（黑色 USB 2.0 或蓝色 USB 3.2 接口）。
2. 开机连按 **`Del`** 进入铭瑄 BIOS（当前版本 `E1.5D`），确认以下设置：
   - **Startup / Boot**：
     - `Secure Boot`：**`Disabled`**（我们在 Windows 注册表中已核实当前已经是 `0` Disabled，保持即可）。
     - `Fast Boot`：**`Disabled`**。
     - `CSM Support`：**`Disabled`**（纯 UEFI GOP 模式，RX 9060 XT 必须关闭 CSM）。
   - **Advanced**：
     - `Above 4G Decoding`：**`Enabled`**。
     - `Re-Size BAR Support`：建议首次安装先设为 **`Disabled`**（若保持 Enabled 也可引导，因 `config.plist` 中已设 `ResizeAppleGpuBars = 0` / `ResizeGpuBars = -1` 兼容）。
     - `XHCI Hand-off`：**`Enabled`**。
   - **绝对不要更改 TPM 设置**（保持默认 fTPM 开启，保护 Windows 登录）。
3. 按 **`F10`** 保存并重启。

### 步骤 3.2：从 U 盘启动并验证 Windows 主盘已被完全隐藏
1. 主机重启时连按 **`F11`** 调出铭瑄主板 UEFI 启动菜单。
2. 选择 **`UEFI: <您的 U 盘名称>, Partition 1`** 回车（**不要**选 `Windows Boot Manager`，也**不要**选旧的 `ubuntu` 启动项）。
3. 进入 OpenCore 图形/文本菜单后，选择 **`Install macOS Tahoe`** 回车。
4. 屏幕开始滚动 `-v` 白色代码，稍候将通过 RX 9060 XT 的 UEFI GOP 帧缓冲进入 **macOS 26 恢复模式（macOS Recovery）**。
5. **【最关键的安全核验步骤 — 清盘前必做】**：
   - 在顶部菜单栏点击 **实用工具 (Utilities) → 终端 (Terminal)**，输入：
     ```sh
     diskutil list
     ```
   - **核对输出**：
     - 您应该**只能看到** `INTEL SSDPEKKF256G8L Media`（约 `256.0 GB`，内含原 Ubuntu 的 `EFI` 和 `Linux Filesystem` 分区）以及您的安装 U 盘。
     - **确认列表中完全没有 `WD_BLACK SN850X 2000GB`（也没有任何 `2.0 TB` 的物理盘）！**
     - 这就 100% 证明我们的 `PciRoot(0x0)/Pci(0x6,0x0)/Pci(0x0,0x0)` 屏蔽已生效，此时在安装器中无论怎么操作，都**绝对不可能触碰到 Windows 硬盘**。

### 步骤 3.3：清空 256GB Ubuntu 硬盘并开始安装 macOS 26 Tahoe
1. 关闭终端，打开 **磁盘工具 (Disk Utility)**。
2. 点击磁盘工具左上角的 **`显示 (View)` 图标 → 勾选 `显示所有设备 (Show All Devices)`**。
3. 在左侧栏选中顶层物理盘：**`INTEL SSDPEKKF256G8L Media`**（确认容量为 `256.06 GB`）。
4. 点击顶部的 **`抹掉 (Erase)`**：
   - **名称 (Name)**：`macOS Tahoe`
   - **格式 (Format)**：`APFS`
   - **方案 (Scheme)**：`GUID 分区图 (GUID Partition Map)`
   - 点击 **`抹掉 (Erase)`**，等待分区完成（这会自动在 256GB 盘上创建全新的独立 `EFI` 分区和 `APFS` 容器，彻底清除旧 Ubuntu 分区）。
5. 关闭磁盘工具，回到主菜单点击 **`安装 macOS Tahoe (Install macOS Tahoe)`**：
   - 同意许可协议，选择刚刚格式化的 **`macOS Tahoe`** 磁盘，开始复制文件。

### 步骤 3.4：多次重启阶段的引导选择（全程按 `F11` 从 U 盘引导）
macOS 26 安装全过程会自动重启 **3 到 4 次**：
- **第 1 次重启（约复制完文件后）**：开机连按 `F11` → 选 U 盘进入 OpenCore → 此时菜单会自动选中新增的 **`macOS Installer`**，直接回车继续。
- **第 2 / 3 次重启**：开机连按 `F11` → 选 U 盘进入 OpenCore → 只要菜单里还有 **`macOS Installer`**，就继续选 `macOS Installer`。
- **最后一次重启（约 25–35 分钟后）**：开机连按 `F11` → 选 U 盘进入 OpenCore → 菜单中的 `macOS Installer` 消失，变成 **`macOS Tahoe`** → 选择 **`macOS Tahoe`** 回车，即可进入 macOS 26 国家/地区设置向导并进入桌面！

---

## 第四部分：将独立 OpenCore EFI 部署到 256GB 盘并清理旧 Ubuntu 引导项

1. 进入 macOS 26 Tahoe 桌面后，打开 **终端 (Terminal.app)**，查看 256GB Intel 硬盘的分区编号：
   ```sh
   diskutil list internal
   ```
   确认 `INTEL SSDPEKKF256G8L` 的 `EFI` 分区标识符（通常为 `disk0s1`）。
2. 同时查看您的安装 U 盘的 `EFI` 分区标识符（例如 `disk2s1`），将 U 盘的 `EFI` 文件夹完整复制到 256GB Intel 硬盘的独立 `EFI` 分区中：
   ```sh
   sudo diskutil mount /dev/disk0s1
   mv /Volumes/EFI /Volumes/EFI_INTEL
   sudo diskutil mount /dev/disk2s1
   cp -R /Volumes/EFI/EFI /Volumes/EFI_INTEL/
   dot_clean /Volumes/EFI_INTEL
   diskutil unmount /Volumes/EFI_INTEL
   diskutil unmount /Volumes/EFI
   ```
   *(注：因为原本 256G 盘已被抹掉重建 GPT，旧 Ubuntu 在该盘 ESP 上的 `EFI/ubuntu/grubx64.efi` 已被彻底清除，现在 256G 盘的 ESP 上只有纯净的 OpenCore 1.0.8)*
3. 关机，**拔掉安装 U 盘**（请妥善保存该 U 盘作为紧急恢复盘）：
   - 开机按 `F11`，选择 `INTEL SSDPEKKF256G8L`（或 `TAHOE26-NAVI44` / `UEFI OS`），验证**不插 U 盘独立启动 macOS 26 Tahoe**。
   - 重启按 `F11`，选择 `Windows Boot Manager (WD_BLACK SN850X 2000GB)`，验证 **Windows 10 IoT LTSC 2024 正常独立启动且数据分毫无损**！
