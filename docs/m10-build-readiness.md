# M10 构建与 M11 条件

现有Python3.11+、Apple Clang21和macOS27 SDK足以运行本轮验证，不需要新SDK或Lilu。
先读取安全约束并使用真实项目文件沙箱；路径检查不替代沙箱。

```sh
python3 -I -B -X utf8 run_m10_checks.py \
  --compiler "$(xcrun --find clang++)" \
  --sdk "$(xcrun --sdk macosx --show-sdk-path)" --target all
```

必须先确认python3>=3.11；本机Xcode Python3.9不能使用，已有其他合格解释器。
显式安全target：host、native、partial-link、all。无默认部署目标；不调用上游Makefile。
host分别构建arm64、x86编译/链接、arm64 ASan/UBSan、生命周期与有限TSan；
native/partial-link根据明确allowlist编译内核对象并审查。每子进程60秒、测试/差分30秒，
Host外层预算600秒且其每个child另有超时，串行编译，输入量固定。

M9原portable helper来自本地固定M9 Git提交，重定向输出到M10，只读其逻辑。
基线、原报告和M9日志不覆盖；旧header回归证明也是从该固定提交只读提取。
当前本地M9历史是复现依赖；将来若发布独立脱敏快照，应明确提供等价公开基线策略。
原始执行日志仅在reports/m10/local，公开JSON标明路径标签替换。
build/tmp、日志包、Apple SDK、Object均不进入Git。

现在具备继续准备M11非部署工程的基础：两架构对象、内部闭合、预期KPI清单和CPU
生命周期模型。尚不能声称完整Kext已可链接/加载。
进一步Full Kext构建须独立授权，并先具备：

- 明确目标Intel macOS/XNU/SDK版本及合法完整链接资料/导出依赖；公共源码参考不能代替。
- 无硬件匹配/初始化的服务/入口骨架、真实owner存储及generation发行约束。
- 真正线程上下文、可阻塞gate、stop/drain/free及IOService引用管理设计。
- 确认OSObject vtable/布局与OSPtr API配置、栈/符号/初始化/KPI依赖。
- 对实际内核prepare/complete、错误恢复、映射/权限撤销仍保留未验证边界。
- 先审查脱敏发布历史；M10本地祖先含原M9私人路径，不能直接推送来满足隐私要求。

本阶段Full Kext Link/Bundle/签名/加载、Kernel/GPU Runtime、Metal、真实显示均NOT RUN。
M11准备不授予签名、安装、加载、EFI/系统变更或硬件实验权限。
