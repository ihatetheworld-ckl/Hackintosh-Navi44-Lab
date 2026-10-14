# Reviewed M9/M10 public snapshot

Parent is the already-public main. Original private M9/M10 commits are absent.
Reports are editorial public copies: PROJECT_ROOT / PYTHON_EXECUTABLE / SDK_ROOT
replace private argv/path prefixes; results and exit codes remain unchanged.
Original local reports/logs are preserved in the development repository.
Selected source is byte-identical to M10 except the public host-check profile:
run_m10_checks.py reads the shipped portable helper and records historical M9
failure calibration NOT RUN because that private commit is deliberately absent.
Native target still requires independently verified pinned export-reference input;
no automatic downloads or manufactured exports. M10 historical source hashes and
privacy-sensitive diagnostic inventories are omitted; original incremental source
patches are replaced by one actual public-baseline patch. Existing public main
history is preserved, without a history rewrite.
