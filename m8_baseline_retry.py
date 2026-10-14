"""Correct only redirected runner import path; preserve failed launcher evidence."""
import sys,runpy,pathlib,json,subprocess,os
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import m7_safety as safe
ROOT=safe.ROOT;out=ROOT/'reports/m8'
safe.write(out/'baseline-first-failure.log',(out/'baseline-reproduction.log').read_bytes())
safe.write(out/'baseline-first-command.json',(out/'baseline-command.json').read_bytes())
text=(ROOT/'run_m7_offline_tests.py').read_text().replace('reports/m7/','reports/m8/baseline/').replace('build/m7/','build/m8/baseline/')
text=text.replace('sys.path.insert(0,str(Path(__file__).resolve().parent))','sys.path.insert(0,'+repr(str(ROOT))+')')
script=safe.write(out/'baseline-runner.py',text)
env=os.environ.copy();env.update(TMP=str(ROOT/'tmp'),TEMP=str(ROOT/'tmp'))
cmd=[sys.executable,'-I','-B','-X','utf8',str(script)]
p=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=120)
safe.write(out/'baseline-reproduction.log',p.stdout+p.stderr)
safe.write(out/'baseline-command.json',json.dumps({'argv':cmd,'exit':p.returncode},indent=2))
if p.returncode:raise SystemExit('Baseline failed')
r=json.loads((out/'baseline/test-results.json').read_text())
safe.write(out/'baseline-results.json',json.dumps({'status':'PASS','scope':'M7 rerun, not M8 new results','result':r},indent=2))
print(json.dumps(r,indent=2))
