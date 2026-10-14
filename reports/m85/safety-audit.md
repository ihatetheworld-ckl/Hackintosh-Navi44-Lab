# M8.5 安全审查

写入仅限原 Lab，未扩大系统权限。安全路径检查及已审查进程 allowlist 属应用层防线，
不是独立目录级 OS 隔离；未进行系统级 IO 追踪，不宣称绝对零副作用。
未修改 Windows/EFI/BIOS/分区/GPU/驱动，未访问第二块 SSD。

原 pipeline 仅 CPU：逐源码编译、Python/C++ 测试、有限变异、Sanitizer 和静态分析。
Darwin Native/device/plugin/硬件 backend 不参与 Host；原硬件 match/init/Makefile 门禁保留。
所有 temp/cache/log 指向项目内，串行并有超时，历史报告 SHA 再核对。
新的便携入口使用显式 source allowlist，无网络、下载、安装、SDK 伪造或系统 API。

Git 从已有受信任安装运行：空 init template、禁 hooks/签名/fsmonitor，
进程内禁用 global/system config、凭据助手、外部属性/忽略规则；只修改 repo-local 配置。
现有 Git 作者身份只用于本地提交元数据，首次推送审核将显示作者资料。
逐文件 stage，检查实际 blob，不传递 token 参数，不运行嵌套上游钩子。
嵌套 .git 保留；ROM、firmware、大工具链及 Workflow 排除。

GitHub connector 只读核实账号/可访问仓库/目标元数据。
Git Credential Manager 仅 --version、help、accounts list，禁交互/trace；
list 因沙箱 wincredman store 不可用失败，无凭据返回。
未进行 login/get/store/erase、外部创建/推送/Actions。
没有私有仓库创建接口；此项是真实工具阻碍，不能报告迁移已完成。

凭据/密钥模式扫描与大小/路径/许可证检查有覆盖边界，不是秘密绝不存在的证明。
源码中公有版权 contact 与必要历史路径归属信息保留；认证文件不进入 Git。
