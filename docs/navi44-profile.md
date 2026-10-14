# Navi44 Profile

1002:7590 → Navi44/gfx1200；1002:7550/7551 → Navi48/gfx1201。未知 vendor/device 拒绝。
revision 可 absent 或明确 0..255；没有实机 revision allowlist，所以 revisionVerified 恒为 false。
GC12.0.0/12.0.1 是上游家族的预期值，不是本机捕获。

C++ topology 全为 0 且 verified=false，零代表 Unknown，不是实际无 CU；Python 不提供活跃 CU/RB/TCC/BAR。
GC_INFO 的 SE/RB 是输入描述，不能当实际启用 topology。capabilities 全为空/零。
identify 与 driver bind 分离：Navi44 match hook 明确 false；任何 OfflineReady 都不授权硬件初始化。
