# M11 非部署文件构造

`run_m11_checks.py`提供显式host / objects / offline-link / all目标。
所有主动输出在项目build/m11、tmp/m11、reports/m11/local；孩子60秒，
用户态行为/差分30秒，有限两线程。既有Python3.11+与Apple工具，禁止自动安装。
历史M9/M10 runner不原地运行；基线副本只重定向到M11并保留原文件。

Native allowlist共17单元：9个纯Core/解析、lifecycle、shutdown、darwin_native、
darwin_snapshot、M8/M10契约、M11抽象IOService/OwnerStorage探针及kmod metadata。
不编译device/plugin/PCI/firmware/GPU/用户态图形工具。两架构均使用真实Kernel头、
C++17、no exceptions/RTTI、mkernel/fapple-kext/no stack protector；x86 no red zone。

Level1：两架构MH_OBJECT。Level2：真实Apple ld -r部分链接。
Level3：x86固定公开导出参考检查；真实目标二进制/SDK ABI未闭合。
Level5的文件构造已执行：Apple ld -kext产生x86 **MH_KEXT_BUNDLE**，
仅保存独立.macho文件，无.kext目录/Info.plist/设备匹配/OSMetaClass注册/签名。
Genuine mach/kmod.h宏声明元数据，项目自己的start/stop入口均返回KERN_FAILURE，
不注册任何服务，全部内核代码绝不执行。该文件不是经过目标KPI闭合验证的完整可部署驱动。

离线文件检查包含CPU/type/load commands/sections/imports/relocations/file/lipo/sha256。
没有LC_MAIN/线程入口/dylib加载/全局构造器/EH表；kmod入口仅是离线符号数据。
Kext输出没有platform build-version命令；报告明确此限制。
禁止把MH_NOUNDEFS标志或ld exit0当作导入已解析。

复现时显式提供已存在、hash核查过的target-export-reference JSON（固定Apple pin见
target-macos-xnu.md）；原文仅本地ignored，没有自动下载。缺少时对象目标拒绝继续。
禁止运行输出、Bundle/deploy/install脚本、签名、kmutil/kextload和硬件步骤。
原root CMake仍只构建用户态CPU目标，本机CMake执行NOT RUN。
