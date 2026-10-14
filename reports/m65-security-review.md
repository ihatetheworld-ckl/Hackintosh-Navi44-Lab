# M6.5 安全审查

项目内写入与CPU-only执行获授权；没有GPU实验授权。

| 行为 | 记录 |
|---|---|
| Windows系统/注册表/服务/AMD驱动修改 | 未执行 |
| EFI/BCD/BIOS/SecureBoot/TPM/BitLocker修改 | 未执行 |
| 磁盘分区/第二SSD Linux读取或修改 | 未执行 |
| GPU BAR/MMIO/VBIOS/ROM/DMA/固件访问 | 未执行 |
| Vulkan/DX/OpenCL GPU提交 | 未执行 |
| Kext/SYS/服务加载 | 未执行 |
| 管理员权限请求/全局PATH修改/系统安装 | 未执行 |
| 项目外显式用户文件写入 | 未执行；系统正常缓存/日志不能承诺零写 |
| Git push/远程PR/Release | 未执行 |
| 便携工具 | 官方archive SHA核验后仅项目内解压 |
| host link | 仅parser/validation/tests，不链接device/plugin/IOKit/GPU API |

init恒false、7590不绑定、Makefile禁用。没有部署产物。
统计与源码hash关联；历史M6报告/patch hash保持；当前PASS不是完整OS安全审计。
完整参考树仍有硬件代码/脚本，未执行。工具链下载digest依赖官方托管metadata，不是独立签名或供应链无风险证明。
canary为自有CPU进程故意heap越界/有符号溢出，不影响GPU；仅验证检测器。
测试timeout/输入规模有限，没有额外建立OS内存Job硬配额或lab专属沙箱。
