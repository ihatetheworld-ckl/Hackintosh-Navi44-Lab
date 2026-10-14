"""Snapshot M7 and redirect its reviewed CPU-only entry into M8 baseline."""
from pathlib import Path
import sys,json,hashlib,subprocess,os
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m7_safety as safe
ROOT=safe.ROOT;OUT=safe.mkdir('reports/m8')
if (OUT/'history').exists():raise SystemExit('M8 snapshot already exists; refusing overwrite')
safe.preflight(['development','tests','docs','patches','tools/toolchains/llvm','tmp','reports/m7','build'])
manifest=json.loads((ROOT/'reports/m7/deliverable-sha256.json').read_text())
for rel,digest in manifest.items():
    with safe.checked(rel).open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest()!=digest:raise SystemExit('M7 hash differs: '+rel)
files=list(ROOT.glob('*.py'))+[ROOT/'README.md',ROOT/'CMakeLists.txt',ROOT/'build_offline.ps1']
for folder in ('development/AMDRadeonRDNA4-Navi44','tests','docs','patches'):
    files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file())
files += list((ROOT/'reports/m7').glob('*.json'))+list((ROOT/'reports/m7').glob('*.md'))
hashes={}
for p in sorted(set(files)):
    safe.checked(p);rel=p.relative_to(ROOT).as_posix();data=p.read_bytes()
    safe.write(OUT/'history'/rel,data);hashes[rel]=hashlib.sha256(data).hexdigest()
safe.write(OUT/'baseline-sha256.json',json.dumps(hashes,indent=2))
historical={}
for p in (ROOT/'reports').rglob('*'):
    if p.is_file() and not p.is_relative_to(OUT):
        safe.checked(p)
        with p.open('rb') as stream:historical[p.relative_to(ROOT).as_posix()]=hashlib.file_digest(stream,'sha256').hexdigest()
safe.write(OUT/'historical-reports-sha256.json',json.dumps(historical,indent=2))
text=(ROOT/'run_m7_offline_tests.py').read_text()
text=text.replace('reports/m7/','reports/m8/baseline/').replace('build/m7/','build/m8/baseline/')
text=text.replace('sys.path.insert(0,str(Path(__file__).resolve().parent))','sys.path.insert(0,'+repr(str(ROOT))+')')
script=safe.write(OUT/'baseline-runner.py',text)
env=os.environ.copy();env.update(TMP=str(ROOT/'tmp'),TEMP=str(ROOT/'tmp'))
cmd=[sys.executable,'-I','-B','-X','utf8',str(script)]
p=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=120)
safe.write(OUT/'baseline-reproduction.log',p.stdout+p.stderr)
safe.write(OUT/'baseline-command.json',json.dumps({'argv':cmd,'exit':p.returncode},indent=2))
if p.returncode:raise SystemExit('Baseline failed; see M8 logs')
result=json.loads((OUT/'baseline/test-results.json').read_text())
safe.write(OUT/'baseline-results.json',json.dumps({'status':'PASS','scope':'M7 rerun, not M8 new results','result':result},indent=2))
print(json.dumps({'baseline':result,'snapshot_files':len(hashes),'historical_logs':len(historical)},indent=2))
