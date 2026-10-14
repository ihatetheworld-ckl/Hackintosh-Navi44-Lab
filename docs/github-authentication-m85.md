# M8.5 官方认证与首次推送方案

本文件是待首次内容确认后的执行方案，当前尚未登录/推送。
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

命令仅为方案，不代表已经执行。不得绕过首次内容确认。
由用户亲自在 GitHub 官方设备授权页面完成登录；不索取明文 PAT。
GCM none 不落盘凭据，Git 消费辅助进程返回的令牌，不把令牌写入 argv/项目。
禁止调用另外的持久化 credential helper 或记录 credential fill 输出。
设备代码提示可在会话展示；完整 Token/HTTP Authorization 不展示、不保存。
授权过程有超时；认证失败则停止，不安装或扩大系统权限。

推送后核实远程 main SHA 与本地相同、Public 为用户允许的状态、无 Workflow；
再用普通提交更新交接记录。此方案的实际设备登录和 Git Push 均为 NOT RUN。
