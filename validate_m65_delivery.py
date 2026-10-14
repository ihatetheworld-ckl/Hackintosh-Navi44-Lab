"""Project-only delivery verification. Does not run builds, devices or GPU APIs."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
R = json.loads((ROOT/'reports/m65/results.json').read_text(encoding='utf-8'))
if R.get('status') != 'PASS': raise SystemExit('Pipeline did not succeed')
for rel, expected in R['source_sha256'].items():
    if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() != expected:
        raise SystemExit('Tested source mismatch: '+rel)
for rel, expected in json.loads((ROOT/'reports/m65/deliverable-sha256.json').read_text()).items():
    if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() != expected:
        raise SystemExit('Deliverable mismatch: '+rel)

documents = [ROOT/'README.md'] + list((ROOT/'docs').glob('*.md'))
documents += list((ROOT/'reports').glob('m65-*.md'))
links = 0
for path in documents:
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
        if target.startswith(('https://','http://','#')): continue
        target = target.strip('<>').split('#')[0]
        if not (path.parent/target).exists():
            raise SystemExit('Broken local link: '+str(path)+': '+target)
        links += 1

environment = os.environ.copy()
environment.update(TMP=str(ROOT/'tmp'),TEMP=str(ROOT/'tmp'),GIT_CONFIG_NOSYSTEM='1',
                   GIT_CONFIG_GLOBAL='NUL',GIT_OPTIONAL_LOCKS='0')
git = Path('D:/RuntimeEnvironment/Git/cmd/git.exe')
if not git.is_file(): raise SystemExit('Existing Git unavailable; no installation attempted')
def check(args,name):
    p = subprocess.run([str(git),*map(str,args)],cwd=ROOT,env=environment,
                       capture_output=True,encoding='utf-8',timeout=20)
    (ROOT/'reports/m65'/name).write_text(p.stdout+p.stderr,encoding='utf-8')
    if p.returncode: raise SystemExit('Patch verification failed: '+name)

upstream = ROOT/'upstream/AMDRadeonRDNA4'
check(['-c','safe.directory='+upstream.as_posix(),'-c','core.hooksPath=NUL','-C',upstream,
       'apply','--check',ROOT/'patches/navi44-m65-offline-cumulative.patch'],'patch-cumulative-check.log')
stage = ROOT/'build/m65/patch-check-baseline'
suffix = 0
while stage.exists():
    suffix += 1; stage = ROOT/('build/m65/patch-check-baseline-'+str(suffix))
stage.mkdir()
history = ROOT/'reports/m65/history'
for path in history.rglob('*'):
    if path.is_file():
        destination = stage/path.relative_to(history)
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,destination)
check(['-c','core.hooksPath=NUL','-C',stage,'apply','--check',
       ROOT/'patches/m65-from-m6-offline.patch'],'patch-incremental-check.log')

for repo in ('AMDRadeonRDNA4','Cobalt64'):
    location = ROOT/'upstream'/repo
    p = subprocess.run([str(git),'-c','safe.directory='+location.as_posix(),'-C',str(location),
                        'status','--porcelain'],cwd=ROOT,env=environment,capture_output=True,
                       encoding='utf-8',timeout=20)
    if p.returncode or p.stdout.strip(): raise SystemExit('Upstream snapshot changed: '+repo)

result = {'status':'PASS','tested_sources_match':True,'deliverable_hashes_match':True,
          'local_links_checked':links,'cumulative_patch_check':'PASS (not applied)',
          'incremental_patch_check':'PASS (not applied)',
          'upstream_snapshots_clean':True,'hardware_and_kext':'NOT RUN'}
(ROOT/'reports/m65/delivery-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
