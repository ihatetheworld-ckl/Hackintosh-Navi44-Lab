# M8.5 官方认证与首次推送方案

本文件记录首次内容确认后的方案与实际执行。首次普通 Git Push 已成功。
目标仅为 ihatetheworld-ckl/Hackintosh-Navi44-Lab，用户已明确接受 Public。
新建/修改其他远程仓库、force push、Actions 不在授权范围。

## 已完成的安全核验

- 现有 Git 2.55.0.windows.4 / Git Credential Manager 2.9.0，不安装工具。
- 默认 wincredman 在沙箱账号不可用；不改 Windows Credential Manager 或全局 Git。
- GCM 官方 2.9.0 支持 `credentialStore=none`：读取/存储均为 no-op。
  此模式只读 accounts list 已实际运行，exit=0，无凭据输出。
- Git 默认 Schannel 在此沙箱读取远程失败；只对命令选择内置 OpenSSL，
  `http.sslVerify=true`，已成功只读 ls-remote；不是关闭证书校验或改变 Windows 安全策略。

官方依据：

- [GCM v2.9.0 credential stores](https://github.com/git-ecosystem/git-credential-manager/blob/v2.9.0/docs/credstores.md#passthroughno-op-no-credential-store)
- [GitHub device 模式配置](https://github.com/git-ecosystem/git-credential-manager/blob/v2.9.0/docs/configuration.md#credentialgithubauthmodes)
- [禁用 GUI、使用文本提示](https://github.com/git-ecosystem/git-credential-manager/blob/v2.9.0/docs/environment.md#gcm_gui_prompt)

## 确认后候选调用

先重新核实 owner、可见性、分支、真实 HEAD 及审核清单。
仅在子进程环境设置（不修改全局环境/PATH，也不写认证文件）：

~~~text
GIT_CONFIG_GLOBAL=NUL
GIT_CONFIG_NOSYSTEM=1
GCM_CREDENTIAL_STORE=none
GCM_GITHUB_AUTHMODES=device
GCM_GUI_PROMPT=0
GCM_TRACE=0
GCM_TRACE_SECRETS=0
~~~

原工具链、TMP/TEMP、hooks 等仍按项目安全边界审查。
真实执行时还需清除继承的 Git/GCM trace/debug/askpass 参数，
明确使用项目内空 hooks、已授权 main SHA 和对应远程 origin：

~~~text
git -c http.sslBackend=openssl -c http.sslVerify=true
    -c credential.helper=manager -c credential.credentialStore=none
    -c credential.gitHubAuthModes=device push -u origin main
~~~

上方 GCM 命令实际尝试后因 Windows 原生 TLS 凭据句柄失败，没有上传代码。
网络权限已在 Codex 本轮授予，未申请额外文件权限或管理员；仍未修复原生 TLS。
由用户亲自在 GitHub 官方设备授权页面完成登录；不索取明文 PAT。
GCM none 不落盘凭据，Git 消费辅助进程返回的令牌，不把令牌写入 argv/项目。
禁止调用另外的持久化 credential helper 或记录 credential fill 输出。
设备代码提示可在会话展示；完整 Token/HTTP Authorization 不展示、不保存。
授权过程有超时；认证失败则停止，不安装或扩大系统权限。

## 实际成功的安全回退

在现有 Windows 工作区沙箱中，使用已有 Python/OpenSSL 和同一受信任 CA，
独立实现 GitHub 官方 device-flow 协议；公开 GCM native-client ID 来自固定
[GitHubConstants.cs v2.9.0](https://github.com/git-ecosystem/git-credential-manager/blob/v2.9.0/src/shared/GitHub/GitHubConstants.cs)。
这是协议兼容辅助程序，不冒称原 GCM 的 .NET TLS 已成功。
没有复制客户端 secret，没有注册新应用，没有安装工具或关闭验证。
参考 [GitHub 官方设备授权协议](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#device-flow)。

用户亲自在 GitHub 完成授权；请求 public_repo。随后在内存中核对账号 login/id、
repo ID/owner/Public/push 权限、已批准 HEAD 和唯一 origin。
Token 不返回对话、不写文件、不写 argv 或 Git config，单次 Git 子进程通过
进程环境中的限定 URL extraHeader 获得它；禁用 credential helper/trace/hooks。
TLS 使用已有 CA、证书验证开启、拒绝重定向；Git pack 串行。
本地辅助程序只保留于 ignored local-history，未改变首次已审核上传文件清单。

真实执行普通 Git push -u origin main；exit=0，远程 SHA
e7a6fb4c92428c9ae4cee893b6f97e3d6b666b74 与本地相同。
GitHub API 逐一核对 388 blob，排除项均未出现；Public 为用户明确允许状态。
最终普通文档同步后进程退出，Token 不持久化；不宣称服务器授权被自动撤销。
Windows 系统设置、全局环境、驱动和 GPU 没有修改。
