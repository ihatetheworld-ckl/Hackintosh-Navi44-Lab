"""Checked project-only snapshots and redirected M6.5 baseline reproduction."""
from pathlib import Path
import hashlib, json, os, subprocess, sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m7_safety as safe
ROOT=safe.ROOT
H=ROOT/'reports/m7/history'
if H.exists(): raise SystemExit('M7 history exists; refusing replacement')
safe.mkdir(H)
old=json.loads((ROOT/'reports/m65/results.json').read_text(encoding='utf-8'))
for rel,expected in old['source_sha256'].items():
    if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()!=expected: raise SystemExit('M6.5 source hash mismatch: '+rel)
for rel,expected in json.loads((ROOT/'reports/m65/deliverable-sha256.json').read_text()).items():
    if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()!=expected: raise SystemExit('M6.5 artifact mismatch: '+rel)
files=[ROOT/x for x in ('README.md','CMakeLists.txt','run_all_offline_tests.py','run_offline.py','build_offline.ps1')]
for directory in ('development/AMDRadeonRDNA4-Navi44/src','development/AMDRadeonRDNA4-Navi44/host','tests','docs','reports/m65'):
    files += [p for p in (ROOT/directory).rglob('*') if p.is_file()]
files += list((ROOT/'reports').glob('m65-*.md'))
hashes={}
for p in files:
    safe.checked(p);rel=p.relative_to(ROOT);data=p.read_bytes()
    safe.write(H/rel,data);hashes[rel.as_posix()]=hashlib.sha256(data).hexdigest()
safe.write(ROOT/'reports/m7/baseline-sha256.json',json.dumps(hashes,indent=2))
# Keep ROOT pointing at this existing lab; route ALL results/runtime logs/builds
# to M7, while reading the already verified M6.5 toolchain provenance.
text=(ROOT/'run_all_offline_tests.py').read_text(encoding='utf-8')
text=text.replace("OUT=ROOT/'reports/m65'; BUILD=ROOT/'build/m65'","OUT=ROOT/'reports/m7/baseline'; BUILD=ROOT/'build/m7/baseline'")
text=text.replace("OUT/'toolchain-provenance.json'","ROOT/'reports/m65/toolchain-provenance.json'")
text=text.replace('log_path=reports/m65/','log_path=reports/m7/baseline/')
safe.preflight(['reports/m7/baseline','build/m7/baseline','tmp'])
script=ROOT/'reports/m7/baseline-runner.py'
safe.write(script,text.replace("ROOT=Path(__file__).resolve().parent","ROOT=Path("+repr(str(ROOT))+")"))
env=os.environ.copy();env.update(TMP=str(ROOT/'tmp'),TEMP=str(ROOT/'tmp'))
p=subprocess.run([sys.executable,'-I','-B','-X','utf8',str(script)],cwd=ROOT,env=env,capture_output=True,encoding='utf-8',timeout=90)
safe.write(ROOT/'reports/m7/baseline-reproduction.log',p.stdout+p.stderr)
if p.returncode: raise SystemExit('Baseline failure; see baseline-reproduction.log')
result=json.loads((ROOT/'reports/m7/baseline/results.json').read_text())
safe.write(ROOT/'reports/m7/baseline-results.json',json.dumps({'status':'PASS','scope':'M7 rerun of M6.5, not new functionality','result':result},indent=2))
print(json.dumps({k:result[k] for k in ('python','cpp_unit','differential','fuzz','sanitizers')},indent=2))
