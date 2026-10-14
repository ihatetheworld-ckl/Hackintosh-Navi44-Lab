# M8.5 剩余事项

1. 用户已创建并提供目标仓库；GitHub 核实 owner 正确、Public、空分支。
   用户明确接受 Public，不再阻塞在 Private 要求。
2. 当前本机 Git 认证未验证：gh/自动化浏览器未提供，GCM store 在沙箱不可用。
   仅允许官方用户认证流程，不安装系统工具、不使用管理员、不索取明文 PAT。
3. 展示真实最终 main SHA、作者、上传清单与审查结论，等待首次推送确认。
4. 有合规认证后仅正常 Git Push；不 force，不触发 Actions，不上传任何未审查内容。
5. 验证远程分支/HEAD/用户允许的 Public 状态，再更新交接文档，报告最终 SHA。
6. Mac 真实构建尚未执行；Apple Clang/SDK、arm64/x86_64、Native object 属下一独立 M9 授权。

本机原开发树、参考仓库、历史快照、工具链、ROM 和日志均保留。
排除上传不等同删除。当前不授权任何 GPU/Kext/macOS/EFI/分区部署。
