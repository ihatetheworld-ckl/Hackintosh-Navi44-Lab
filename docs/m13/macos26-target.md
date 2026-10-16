# M13 正式目标

正式研发目标为macOS26 Tahoe / Intel x86_64 / Navi44 gfx1200 / PCI1002:7590。
静态构建固定26.5；最终安装版本未选择。开发Host仍为arm64 macOS27.0.1。
配置唯一入口config/m13-target.json；README/AGENTS/CMake及新runner已迁移。
M6–M12原始报告不修改；SDK27/minos15仅用于明确标记的legacy基线或隔离负样本。

Apple `macos-265`分发commit `83390100289cedfe669c31a96c94326d31afa1ed` 的xnu gitlink
为 `ac9718fb1af618d5ce8678d0dc6e8a58f252216f`，提交名xnu-12377.121.6。
26.0的xnu-12377.1.9已重新核对，不能套用于26.5。
[固定分发树](https://github.com/apple-oss-distributions/distribution-macOS/tree/83390100289cedfe669c31a96c94326d31afa1ed)
与[固定XNU](https://github.com/apple-oss-distributions/xnu/tree/ac9718fb1af618d5ce8678d0dc6e8a58f252216f)。

Apple [Tahoe兼容列表](https://support.apple.com/en-us/122867)包含部分Intel Mac，
不认证i5-12600KF/B760M PC。无核显、唯一显卡的恢复要求属于未来独立硬件授权条件。
本轮不接触Windows、第二SSD、引导或GPU。
