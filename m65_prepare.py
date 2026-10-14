"""Local-only M6.5 history capture and baseline run; no hardware operations."""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys, os
ROOT=Path(__file__).resolve().parent
history=ROOT/'reports/m65/history'
if history.exists(): raise SystemExit('History already exists: refusing overwrite')
history.mkdir(parents=True)
paths=['README.md','CMakeLists.txt','run_offline.py','build_offline.ps1',
       'tests/test_offline.py','tests/unit/host_tests.cpp','tests/fixtures/synthetic.py',
       'reports/test-results.json','reports/test-log.txt','patches/navi44-offline-prototype.patch']
paths += [str(p.relative_to(ROOT)) for p in (ROOT/'development/AMDRadeonRDNA4-Navi44/src').glob('*') if p.name in
          ('asicprofile.hpp','offlinefirmware.hpp','codeobj.cpp','codeobj.hpp','ipdiscovery.cpp','ipdiscovery.hpp')]
paths += ['development/AMDRadeonRDNA4-Navi44/host/navi44.py']
hashes={}
for rel in paths:
    src=ROOT/rel; dst=history/rel; dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(src,dst); hashes[rel]=hashlib.sha256(src.read_bytes()).hexdigest()
(history/'baseline-sha256.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
env=os.environ.copy(); env.update(TMP=str(ROOT/'tmp'),TEMP=str(ROOT/'tmp'))
result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'tests/test_offline.py')],cwd=ROOT,
                      env=env,capture_output=True,text=True,timeout=30)
(ROOT/'reports/m65/baseline-python.log').write_text(result.stdout+result.stderr,encoding='utf-8')
print(result.stdout+result.stderr)
sys.exit(result.returncode)
