# M9–M13 sanitized publication

Based only on public fd9b90328f7f94d224995cc7fe70f3cb2605e577. Original private M9–M13 development commits are not ancestors. Exact C++/Python/config snapshot matches the reviewed development files. Reports have path-label substitutions; raw SDKs, source reference dumps, binaries, credentials and raw logs are excluded. The prior public M10 compatibility profile is retained; .gitignore adds local QA exclusion.

Independent publication Host QA under existing SDK26.5: C++161+74+59+34+54, Python91 PASS/2 SKIP, differential744, parser2400, display/query3200, DisplayID500, ASan/UBSan/TSan PASS within coverage. x86 compile/link PASS, x86 runtime NOT RUN. Publication Native QA NOT RUN; copied Native evidence is explicitly development-tree evidence. No deployment or GPU execution.

This branch is a local reviewed candidate. A separate human approval for its exact commit/ref is required before any push. No main merge, force, CI, SDK or system operation.
