# 固定上游、用途与许可证

本文件记录实际固定来源；不表示这些提交是当前最新版本。参考克隆在本机保留，
主仓库不含其 `.git`、子模块 gitlink、固件或 ROM。禁止自动获取或执行依赖脚本。

| 项目 | 固定提交 | 用途 / Mac 是否需要额外获取 | 许可证 |
|---|---|---|---|
| [AMDRadeonRDNA4.kext](https://github.com/RX4Darwin/AMDRadeonRDNA4.kext) | `49f7f20c00dd154384418078f8a09e79c400a06a` | 衍生源码在 `development/AMDRadeonRDNA4-Navi44`；CPU Host 不需额外克隆 | BSD-3-Clause；保留根和衍生目录 LICENSE，局部例外见 NOTICE |
| [Cobalt64](https://github.com/Almosst-DEV/Cobalt64) | `d6c9aedf8e6526a39e349b5886cbc8c7ddf77f65` | ABI/图形路线参考，不是 Host 构建依赖；未来审计可独立获取固定版本 | 顶层 MIT，具体文件/目录条款可能不同；完整克隆未纳入 |
| [Lilu](https://github.com/acidanthera/Lilu) | `0515f40b7f2a096adc85e832a4c6104fbd07f936` | 上游子模块 pin 已通过 `git ls-tree` 核实；未来真实 Kext 集成依赖，Host 不需要 | BSD-3-Clause；获取时保留上游 LICENSE，未把完整源码纳入 |
| [MacKernelSDK](https://github.com/acidanthera/MacKernelSDK) | `05094e5e88cec7caedbfb35e8449ed0db94bf95b` | 同上，未来 Darwin Native 构建需要合法固定头文件；不能代替真实 Apple SDK | 上游为混合 Apple/第三方内核头文件，按每个文件及上游 License/目录声明；本次未重分发其源码 |
| [LLVM](https://github.com/llvm/llvm-project) | `87f0227cb60147a26a1eeb4fb06e3b505e9c7261` (`llvmorg-20.1.8`) | `upstream/references/llvm-ELF.h` 仅作为 ELF 常量测试的静态文本参考，不参与 C++ include | Apache-2.0 WITH LLVM-exception；`licenses/LLVM-LICENSE.txt` |
| [Linux](https://github.com/torvalds/linux) | `24a19b953e2a3d0ea5a8c4951a0ab8f32720c907` | `upstream/references/linux-discovery.h` 为静态格式参考，非 Host 构建依赖 | 该文件内 AMD MIT 许可；不把 Linux 整体许可证混用于单文件 |
| [Mesa](https://gitlab.freedesktop.org/mesa/mesa) | `f5cb8ee032adabef599ae892ec4e42d796b84da9` | 衍生目录保留上游 `vulkan/mesa-patches` 与归属说明；不执行 build-mesa.sh，不是 Host 依赖 | 补丁目录说明为 MIT；未来完整 Mesa 应分别核对文件条款 |
| [LLVM-MinGW](https://github.com/mstorsjo/llvm-mingw/releases/tag/20261006) | `20261006` / Clang `23.1.3` | Windows 便携工具链未上传；既有本机无需重装。Mac 使用 Apple Clang | 多组件许可证，本地原包保留；仓库只保留来源记录 |

LLVM-MinGW 原包 `llvm-mingw-20261006-ucrt-x86_64.zip`：
190,836,485 bytes，SHA-256
`317492c456aa27ee607a5919f1d2d38dcdc1112516a24d0bf4b00d078f52d17a`。
历史来源证明见 `reports/m65/toolchain-provenance.json`。不自动调用下载/安装；
根目录保留的历史一次性 acquisition/finalizer 脚本仅用于研发追溯，禁止自动执行。

LLVM ELF 参考 SHA-256：
`ff0685fe6d5a62a2df2df41eb278330153e2d0a52e573ae02cdcd56c3b6b579c`。
Linux Discovery 参考 SHA-256：
`032d97c699c9378edb64b005ddc53ab08763b853f6b64fcdb0a71dd7999b98e5`。
LLVM 许可证文本来自已保留便携包的 LLVM LICENSE.TXT；
已对照[固定 LLVM 提交的官方许可](https://github.com/llvm/llvm-project/blob/87f0227cb60147a26a1eeb4fb06e3b505e9c7261/llvm/LICENSE.TXT)的 Apache/LLVM exceptions 条款。

上游 Cobalt PR12 参考 head `2c3bba7771ed0d51dc01a6882987a4cfbbd1afe2`：
历史审计时 open/unmerged，未应用。不能据此声称主线已具备该功能。

未来获取依赖须在经授权的独立目录内，核对 URL、提交、LICENSE、路径和脚本，
不得自动运行子模块钩子、安装器、Kext 或硬件初始化。
本仓库不提供 ROM、GPU firmware、Apple 私有源码或非官方 Apple SDK。
