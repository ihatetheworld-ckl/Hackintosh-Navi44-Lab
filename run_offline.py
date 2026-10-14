"""Reviewed CPU-only test runner. Writes reports solely inside this lab."""
from pathlib import Path
import importlib.util
import io
import json
import sys
import unittest
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('labtests',ROOT/'tests/test_offline.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
stream=io.StringIO()
suite=unittest.defaultTestLoader.loadTestsFromModule(module)
result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
summary={'scope':'Python CPU-only synthetic/logic tests; NOT C++ or GPU verification',
         'python':sys.version,'tests':result.testsRun,
         'PASS':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
         'FAIL':len(result.failures)+len(result.errors),'SKIP':len(result.skipped),
         'skipped':[(str(t),reason) for t,reason in result.skipped],
         'NOT RUN':['C++ compilation (no compiler found)','macOS kext build (no SDK)',
                    'GPU initialization/submission/display/Vulkan/Metal/WindowServer (not authorized)']}
(ROOT/'reports/test-log.txt').write_text(stream.getvalue(),encoding='utf-8')
(ROOT/'reports/test-results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(stream.getvalue())
print(json.dumps(summary,ensure_ascii=False,indent=2))
sys.exit(0 if result.wasSuccessful() else 1)
