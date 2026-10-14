# M9–M11 source snapshot

This extends the clean M9/M10 publication commit by exact file export, without
merging original private commits. Public reports use PROJECT_ROOT / SDK_ROOT /
PYTHON_EXECUTABLE labels. Original raw logs remain in the development repository.
All M11 C++/tests and run_m11_checks.py are byte-identical to the original M11.
Existing public run_m10_checks.py keeps its history-free profile (old private
failure calibration NOT RUN). Native export-reference data is an explicit local
input, not automatically downloaded. Publication QA runs the actual shipped M11
CPU source with output paths redirected to ignored publication/local only.
No M12 experimental source, SDK/header copy, binary, credentials, or raw logs
are exported. Full target ABI and kernel/GPU runtime remain unverified/not run.
