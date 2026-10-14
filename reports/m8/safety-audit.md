# M8 安全审查

唯一主动写入边界：D:/CodexWorkSpace/黑苹果研究/Hackintosh-Navi44-Lab。
已确认当前workspace-write沙箱允许范围比Lab更广，不宣称OS级Lab专属隔离。
人工审查每个命令，固定源码/进程allowlist，写入前执行真实路径/父目录检查；
拒绝..、越界resolve、symlink/reparse/junction与多hardlink。不能抵御独立并发TOCTOU攻击。
无法确认安全的设备/SDK/远程操作没有执行；没有请求Full Access或权限提升。

实际进程：既有Python、Lab中核对过归档的Clang/nm/symbolizer、本项目CPU-only exe、
只读Git status/rev-parse、项目副本Git apply。没有执行上游完整构建/安装脚本。
M8 runner从旧runner明确边界导入已审查helper，重定向所有M7输出，
不执行旧report writer。历史文件hash核对，最终验证旧gate源码字节未改。
Host源码只列Core与EDID/Atom纯解析，排除device/plugin/IOKit/native GPU API。

TMP/TEMP/cache及sanitizer日志指向Lab，Python -B。每子进程30/40秒，串行固定种子，
fuzz有限2400+800，已有变异2400，非无限/性能压力。一个16MiB+1测试buffer用于budget边界，
不通过放宽Host1MiB传输限制完成差分。失败保留于attempts，不关闭Sanitizer。
只有本项目canary进程发生预期异常；未结束用户其他进程。
CMake显式CPU source、无fetch/install/custom/pre/post hooks；新增CTest串行30秒。
CMake/MSVC/native SDK构建未执行。compiler CFG与runtime重新对照已有ZIP。

| 禁止操作 | 本代理执行记录 |
|---|---|
| 工作区外主动写入 | 未执行；无独立系统级审计 |
| Windows系统/注册表/服务/驱动/安全策略修改 | 未执行 |
| EFI/BCD/BIOS/UEFI/TPM/Secure Boot/BitLocker修改 | 未执行 |
| SSD分区/Intel第二盘内容访问 | 未执行 |
| GPU BAR/MMIO/ROM/VBIOS/DMA/固件/命令 | 未执行 |
| DDC/I2C/AUX或显示配置变更 | 未执行 |
| SYS/Kext注册/加载/安装 | 未执行 |
| 管理员/全局PATH/Git配置 | 未执行 |
| 未授权远程设备/代码推送/PR/Release | 未执行 |
| 远程第三方代码执行/系统安装 | 未执行 |

网络仅网页阅读；未下载/运行新工具链、Apple SDK或上游脚本。
操作系统和工具可能产生缓存、日志、故障报告，未有独立系统级观测，
因此不承诺物理零写入或绝对零副作用。
