# Navi44 Lab 安全开发约束

当前项目是 CPU-only 离线研发。新会话先读取 README、UPSTREAM_SOURCES.md、
docs/macos-codex-handoff.md、最新 reports/m85/development-report.md 和 M8 安全报告。
本文件不能自动授予新机器、驱动部署或硬件实验权限。

- M13用户正式目标为macOS26 Tahoe/x86_64；静态基线26.5，配置见config/m13-target.json。
- 当前构建显式选择已有SDK26.5，拒绝默认SDK27和旧15导出参考；历史复现须标记legacy。
- 不改M6–M12原报告；仍不下载SDK/KDK，不执行内核/设备/GPU代码，发布仍需独立确认。

- 写入仅限用户在当前会话明确授权的项目目录；检查父目录真实路径、链接和硬链接。
- 不改系统、全局 PATH/Git 配置、EFI/BIOS/分区、安全策略。
- 不读取 GPU ROM/BAR/MMIO，不执行 DMA/固件上传/图形/计算/显示配置变更。
- 不安装、签名、注册或加载 Kext/SYS；不运行用户态 GPU 程序。
- Host 只使用根 CMakeLists 的 CPU 源码 allowlist；Darwin Native 必须独立标记。
- 不运行旧 finalizer/prepare/report writer 覆盖历史；新增阶段单独保存记录。
- 不运行未经审查的上游 Makefile、Shell、依赖钩子或自动下载/安装脚本。
- 无异常/无 RTTI 检查通过不等于 Darwin 内核 ABI 通过；Mac Host 不等于 Kext。
- 合成 Fixture 不等于 Navi44/真实显示器实测；保留 SKIP/NOT RUN/UNVERIFIED。
- 保留原许可证、固定 pin、门禁、源码补丁和有界测试断言。
- 不创建/运行 GitHub Actions，不 force push，不自行改变仓库可见性。
- 用户已明确允许 ihatetheworld-ckl/Hackintosh-Navi44-Lab 使用 Public；
  此例外仅适用于该目标，首次推送仍需完整清单确认。
- 首次推送必须按用户指令展示并确认具体内容。敏感信息和 ROM/firmware 禁止上传。
- 需要扩大授权时停止对应操作，继续其他已授权安全任务。
