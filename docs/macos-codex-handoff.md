# Mac Codex 交接（首次推送前版本）

- 连接账号已核实：`ihatetheworld-ckl`。
- 预定仓库：`https://github.com/ihatetheworld-ckl/Hackintosh-Navi44-Lab`。
- 目标分支：`main`。
- Private：必须在首次推送前通过实际仓库元数据确认。
- 远程推送：尚未执行；必须先获得用户对完整内容的确认。
- 固定提交：首次本地提交 SHA 记录于 Windows 本地
  `reports/m85/local-commit.json` 和最终对话；本文件不能嵌入自身所在提交的 SHA。
  推送成功后，将真实交付提交记录纳入后续普通提交，再报告最终远程 HEAD。

仅在仓库实际存在、Private 已验证且代码已获准推送后，在经授权的 Mac 工作区使用：

~~~sh
git clone https://github.com/ihatetheworld-ckl/Hackintosh-Navi44-Lab.git
cd Hackintosh-Navi44-Lab
git switch main
git rev-parse HEAD
~~~

认证由用户通过 GitHub 官方流程完成，禁止把 Token 写入命令、项目或报告。
不使用 `--recurse-submodules`：本仓库没有活动子模块。
如提供了固定交付 SHA，再核对 HEAD 或在独立目录检出该 SHA，不覆盖其他项目。

源码在 `development/AMDRadeonRDNA4-Navi44/{core,src,host,platform}`，
测试在 `tests`，固定来源在 UPSTREAM_SOURCES.md，M6–M8 总结/patch 均保留。
完整 upstream、工具链、固件/ROM、原机器大日志与快照只保留于 Windows，
历史文档指向这些文件的链接在克隆中可能不存在；这不影响 CPU Host 源码依赖。

先读 AGENTS.md、README.md、docs/macos-build-preparation.md、M8/M8.5 报告；
只读运行 `xcrun clang++ --version` 核实真实 Apple 工具链。
按编译准备文档推进 M9：arm64 Host → x86_64 Host → 合法 Native object。
Mac 的构建/运行在 Windows 本轮均为 NOT RUN。

重要阻碍：真实 Code Object/ROM/IP/topology 尚缺、DisplayID 等未支持、
ABI/Native 对象未经过 Mach-O/IOKit 实际编译，Cobalt N44Q 非生产接口。
本次迁移不授权安装/签名/加载 Kext，不授权 GPU 或显示输出实验。
不得运行衍生目录 hardware/userspace/vulkan 工具，不能解除现有硬件初始化门禁。
