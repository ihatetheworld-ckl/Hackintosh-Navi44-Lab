# 实际离线测试结果

日期：2026-10-13。Python 3.12.13，CPU-only，无第三方依赖。

| 状态 | 数量/范围 |
|---|---|
| PASS | 56 项真正执行的Python测试 |
| FAIL | 0 |
| SKIP | 2：真实Navi44 Discovery、真正shader产物缺失 |
| NOT RUN | C++编译、macOS Kext构建、全部硬件功能 |

总数 58。包括1000次确定性输入变异、所有截断长度、多类错误输入、profile/firmware/ELF/ABI和失败状态。

实际命令：`& 'D:\RuntimeEnvironment\mise\mise\data\installs\python\3.12.13\python.exe' -I -B run_offline.py`
完整日志：[test-log.txt](test-log.txt)，机器可读：[test-results.json](test-results.json)。
Python测试不证明C++正确；输入变异不是完整fuzz覆盖；所有fixture均合成。
