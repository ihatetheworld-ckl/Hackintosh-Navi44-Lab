# M8.5 GitHub 迁移准备完整报告

## 实际完成状态

本阶段继续使用原 Hackintosh-Navi44-Lab，没有重新开发 GPU 驱动。
项目根和祖先均无已有 Git 工作树；根仓库现已初始化为 main。
开发副本/upstream/历史快照中的独立 .git 保留，不进入主仓库。
首次远程推送必须经用户确认，当前没有远程上传。
本地固定源码基线：a4d8a30c7bf30709b40ac2d146f29402918020c9，
标题 Initial import: Navi44 M8 offline development。
此固定源码基线有 386 普通文件，5,928,388 Git blob bytes（约 5.65 MiB），
无 gitlink/symlink、工具链/ROM/Workflow；扫描无已知敏感模式发现。
后续交接文档提交仅补充真实基线 SHA 与本段记录，最终 main HEAD 在对话提供。
用户随后提供仓库并接受 Public。为遵守不发布私人数据的要求，
未上传的首次提交仅重建作者/提交者元数据，保留完全相同源码 tree：
e2c4208fb36405633bc6fad45c56fb15c9811529。
作者仍为 bangbangckl，邮箱改为 230952569+ihatetheworld-ckl@users.noreply.github.com，
只改仓库本地配置，旧对象只在本机 reflog/unreachable history，不会随 main 正常推送。
此为推送前隐私处理，没有修改远程历史，也没有使用 force push。

已创建 .gitignore/.gitattributes、根 LICENSE/NOTICE、UPSTREAM_SOURCES.md、
Mac 编译准备/交接文档、项目 AGENTS.md、两种安全 CPU 验证入口及本地迁移审核工具。
README 改为跨平台项目说明，原 README 快照在本机保留。
Core/Host/Platform、EDID/AtomBIOS/Firmware/ELF、N44I/N44Q 研发代码原字节未改。

## 项目、范围与路径审查

唯一主动写入边界为原 Lab 及真实子目录。实际 workspace-write 授权比 Lab 更广，
不宣称已经建立 Lab 专属系统级隔离。
路径预检拒绝 ..、越界 resolve、symlink/reparse/junction、多 hardlink。
全树只读遍历没有发现链接逃逸；不依赖符号链接移动文件，不删除上游元数据。
Git 运行前检查新 .git 和父目录，使用空模板及空 hooks 目录，
进程内隔离全局/系统 Git 配置、禁止签名/hooks/filters/凭据助手，不修改全局设置。
真实 Git 2.55.0.windows.4；沿用既有 Git 姓名，Public 发布采用账号 ID 对应 noreply，
不借用上游作者身份。

## 上传内容与保留策略

保留：

- 开发副本 Core/Host/Platform、解析器、原门禁及所需源文件。
- C++/Python 测试、合成 Fixture、CMake、Windows 离线入口、便携 Host 入口。
- M6/M6.5/M7/M8 关键报告、来源/哈希/命令记录，五份历史源码补丁。
- 上游版权、局部许可证、两份静态公开参考头文件。
- 跨平台 README、M9 准备/交接、安全约束与迁移证据。

排除但**不删除本地原件**：

- build/tmp、190 MB 工具链 ZIP 及完整便携环境、exe/dll/obj/pdb/库。
- 完整参考克隆、嵌套 .git、未获取的 Lilu/MacKernelSDK 子模块路径。
- 开发副本中的 RX9070XT ROM、整个 firmware 目录、上游硬件 capture 大日志。
- 历史原始快照/attempts/execution 与可再生大输入；重要总结和补丁仍保留。
- 上游 emulator、部署/硬件工具脚本和 build-mesa.sh；原硬件源码仅用于静态研究。
- 所有 .github、Workflow、认证/密钥/账号配置。

仅允许一个明确的 bin：tests/fixtures/m65-invalid-strtab.bin，为已审计的合成 ELF 损坏回归。
源代码中的上游生成 shader 数组随许可证保存，非固件，也不代表 gfx1200 已验证。
fwblobs.S 只有公开路径/符号引用，不包含 firmware payload；不加入 Host。
实际进入 Git 的数量/大小/类别及 blob SHA 由本地上传审核清单记录，最终对话提供准确值。

## 许可证和上游固定版本

AMDRadeonRDNA4 为 BSD-3-Clause，根及开发目录 LICENSE 保留原版权。
新代码沿用历史 BSD 政策。Mesa 补丁目录及 Navi48 MIT 通知保留。
LLVM ELF.h 的 Apache-2.0 WITH LLVM-exception 许可文本补齐；Linux Discovery.h 保留 AMD MIT。
不把所有代码统一改成一个许可证。Cobalt64/Lilu/MacKernelSDK 完整源码未重分发，
未来获取仍须按各文件/目录条款复核；不存在新的 Apple SDK/私有源码来源。
排除的 emulator 许可证不被根 BSD 掩盖；原件和来源仍可本机审查。
具体 URL/commit/用途见 ../../UPSTREAM_SOURCES.md。

## 实际 CPU-only 回归

迁移前 54 个 M8 交付哈希、940 个 M6/M6.5/M7 历史报告哈希匹配。
修改后只有 README 发生预期变化；940 历史报告和所有受清单覆盖的其他 M8 文件仍一致。
原 M8报告、patch 和历史测试原件均未覆盖。

真实执行：

~~~text
python -I -B -X utf8 run_m85_offline_tests.py
python -I -B -X utf8 run_host_tests.py --compiler <existing-lab-clang++.exe> --stage m85-host
~~~

实际编译器为 LLVM-MinGW 20261006 / Clang 23.1.3。
旧 pipeline 被只读导入并明确重定向到 reports/m85/validation、build/m85/validation。
136 个有超时的 pipeline 子命令无非预期失败；Sanitizer canary 预期非零不计失败。

| 类别 | 本轮实际重跑结果 |
|---|---|
| Python | 91 PASS、2 SKIP；其中 4 PASS 是静态安全检查 |
| C++ 单元 | 34 + 31 + 96 = 161 PASS |
| 差分 | 743 + 1 = 744 组，零差异 |
| 有界变异 | 原 2400 + 显示/ROM 2400 + Query 800；固定种子 |
| ASan/UBSan | 当前有限覆盖通过，canary 检出预期错误；leak 未验证 |
| 静态分析 | M8 十个检查文件零 warning；原回归四文件也执行 |
| Core/Contract | 无异常/无 RTTI/freestanding Host 编译及符号检查通过 |
| 便携入口 | Windows 实际编译/运行通过；重复 161 C++ 不累计为新增断言 |
| Mac/Native/Kext/GPU | NOT RUN |

详细结果见 test-results.json，真实 argv/exit 见 validation-commands.json。
完整日志保留于本机 validation 和 reports/m85-host（不上传）。
便携入口没有复用 Windows DLL/ZIP 依赖；Mac 分支尚未实际执行。
另外通过 checkout-index 将已审核 index 的 381 文件导出到项目内干净目录，
不复制工具链、完整 upstream 或嵌套 .git，再使用现有可信编译器验证：
Python 四套和 C++ 161 断言、3200 有界变异、Core/Contract 编译均通过。
这是 Windows 干净源码导出验证，不是 Mac 实测；重复断言不累计为新增测试。
第一次导出字节核对发现 18 个 text=auto 文件被 Windows 转成 CRLF，
它们转回 LF 后都与 index 匹配，功能测试通过。这不是源码丢失或解析错误。
保留失败清单 source-export-first-hash-check.json；将默认属性补为 text=auto eol=lf，
然后重新导出并做逐字节 SHA 核对。
真实命令见 source-export-command.json、source-export-lf-command.json
及 source-export-host-commands.json；输出摘要见 source-export-results.json。
真实 gfx1200 Code Object/Discovery Fixture 继续 SKIP；ROM 和显示器数据没有采集。

## Git 管理和跨平台

使用精确逐文件 manifest 分批 git add，不使用 add . 或 add -A。
首次 stage 后实际 index 只有 140 文件，比已审查清单少 241 个开发源文件：
Git add 跳过嵌套 .git 的后代。检查在 commit 前发现并阻止缺源码提交。
原不完整 index blob 清单留在本机 local-history/incomplete-first-stage.json。
保留原嵌套元数据，用逐文件 hash-object --path/--stdin 和 update-index 注册普通 blob，
不创建 gitlink，不删除/移动嵌套 .git；新增 index 与审查 manifest 必须完全一致的断言。
stage 前扫描工作区候选，stage 后读取实际 Git blob 再扫描；
检查禁止扩展名、credential URL、已知 token/private key/SID、大小、
大小写/Unicode 冲突、symlink/gitlink、Workflow 和来源许可证。
模式扫描不能证明任意秘密绝不存在；未把扫描 PASS 等同独立系统审计。

文本在 Git 内规范为 LF，不改写既有工作区源码；patch/bin 保留字节。
历史源文件 SHA 为当时 Windows 工作区字节，不代表 Git LF 版本；分开保存迁移 blob 证据。
根 CMake 相对路径且 source allowlist 完整，不依赖完整 upstream 克隆。
测试所需 LLVM 参考文本明确纳入，不能误排除。
部分历史文档指向大日志/快照的链接仅在原机有效，README/交接文档已说明。

## GitHub 当前阻碍

已通过连接核实账号 ihatetheworld-ckl；未猜测用户名。
初始元数据查询返回 404；用户后来通过浏览器创建并提供链接。
最新 GitHub API 已核实仓库 ID 1418325342、owner ihatetheworld-ckl、
visibility=public、private=false、branches=[]。仓库是已授权用户的空白目标。
用户明确回复“public就public”，本次按 Public 继续，仍须首次上传清单确认。
没有 gh 可执行文件、浏览器自动化工具或创建仓库的连接接口。
已检查既有 Git Credential Manager 2.9.0 的只读 accounts list；
其在沙箱账号下因 wincredman store 不可用失败，未取得凭据。
未调用 login/get/store/erase，未读取 Token，未触发设备授权或认证写入。
当前进程没有 GH_TOKEN/GITHUB_TOKEN（只检查是否存在，未输出任何值）。

仓库已由用户创建，不再需要创建接口。当前 Windows Git 认证仍未验证，
连接中的已认证权限不等于本机 Git 已有凭据。
没有下载/安装 gh、扩大权限、冒用连接内部凭据或把 Token 写入项目。
下一步先展示具体 main/HEAD/数量/体积并获首次推送确认；
若认证需要用户操作，只允许官方浏览器/设备流程，不索取明文 Token。
禁止 force push、覆盖其他仓库历史或确认前传送 blob/tree/源码。

## Mac M9 交付

纯 Host 源码完整；Mac 需已有 Python 3.11+ 与 Apple Clang，CMake 为可选既有工具。
纯逻辑不需要额外克隆 Lilu/MacKernelSDK/Cobalt64；Native object 后续才需要固定依赖。
Apple Silicon arm64 Host 与 x86_64 Host/Target 必须独立报告。
M9 应优先验证真实 Apple Clang/SDK/Native object，避免继续堆积未编译硬件代码。
本次交接不授权安装/签名/加载 Kext、访问 GPU/EFI/分区或在其他设备自动操作。

## 安全执行记录

| 操作 | 本阶段记录 |
|---|---|
| 主动写入工作区外 / 系统配置 / 全局 Git/PATH | 未执行 |
| Windows 驱动/服务/注册表、安全策略 | 未修改 |
| EFI/BIOS/BCD/TPM/BitLocker/SSD 分区/第二盘读取 | 未执行 |
| GPU ROM/BAR/MMIO/DMA/初始化/显示/计算 | 未执行 |
| Kext/SYS 安装、签名、加载 | 未执行 |
| 管理员/安装系统工具/第三方脚本远程执行 | 未执行 |
| GitHub 创建/上传/推送/Actions/PR/Release | 仓库由用户创建；本代理仅只读核实，未上传/推送/运行 Actions |
| 本地 Git init/config/精确 add/commit | 授权范围内；具体执行见本地 Git 记录 |

仅执行审查后的 CPU 编译/测试和已有 Git/官方 GCM 查询。
没有独立系统级追踪审计，不能承诺 OS/工具缓存与日志绝对零副作用。
完成本地交付后停在首次推送确认边界；本机 Git 官方认证可能仍需单独完成。
