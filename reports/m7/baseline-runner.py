"""M6.5 reviewed CPU-only pipeline. Explicit paths, no shell/install/device calls.
Only verified portable compiler and our own host binaries are executed.
All compiler temp/cache/output/log paths stay under this project.
"""
from pathlib import Path
import hashlib, importlib.util, json, os, random, shutil
import struct, subprocess, sys, time, re
from datetime import datetime, timezone, timedelta
ROOT=Path('D:\\CodexWorkSpace\\黑苹果研究\\Hackintosh-Navi44-Lab')
OUT=ROOT/'reports/m7/baseline'; BUILD=ROOT/'build/m7/baseline'
OUT.mkdir(parents=True,exist_ok=True); BUILD.mkdir(parents=True,exist_ok=True)
BIN=ROOT/'tools/toolchains/llvm/llvm-mingw-20261006-ucrt-x86_64/bin'
CPP=BIN/'clang++.exe'; SRC=ROOT/'development/AMDRadeonRDNA4-Navi44/src'
ENV=os.environ.copy()
ENV.update(TMP=str(ROOT/'tmp'),TEMP=str(ROOT/'tmp'),CLANG_MODULE_CACHE_PATH=str(BUILD/'cache'),
           ASAN_OPTIONS='halt_on_error=1:detect_leaks=0:log_path=reports/m7/baseline/asan',
           UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1:log_path=reports/m7/baseline/ubsan',
           ASAN_SYMBOLIZER_PATH=str(BIN/'llvm-symbolizer.exe'))
commands=[]

def unittest_counts(log):
    """Count executed outcomes, keeping source-only checks separate."""
    run_count = re.search(r'Ran (\d+) tests?', log)
    if not run_count: raise RuntimeError('Missing unittest execution summary')
    rows = re.findall(r'^test_\w+ \(([^)]+)\) \.\.\. (.+)$', log, re.MULTILINE)
    passed = sum(outcome == 'ok' for _, outcome in rows)
    skipped = sum(outcome.startswith('skipped ') for _, outcome in rows)
    failed = sum(outcome in ('FAIL', 'ERROR') for _, outcome in rows)
    static = sum('.SafetyTests.' in name and outcome == 'ok' for name, outcome in rows)
    count = int(run_count[1])
    if count != passed + skipped + failed:
        raise RuntimeError('Unittest log totals do not match executed rows')
    return {'tests': count, 'PASS': passed, 'FAIL': failed, 'SKIP': skipped,
            'static_checks': static, 'behavior_PASS': passed - static}

def source_manifest():
    paths = [ROOT/'run_all_offline_tests.py', ROOT/'CMakeLists.txt',
             ROOT/'tests/test_offline.py', ROOT/'tests/test_m65.py',
             ROOT/'tests/fixtures/synthetic.py', ROOT/'tests/unit/m65_unit.cpp',
             ROOT/'tests/unit/m65_probe.cpp', ROOT/'tests/unit/sanitizer_canary.cpp',
             ROOT/'development/AMDRadeonRDNA4-Navi44/host/navi44.py']
    paths += [SRC/name for name in ('asicprofile.hpp','ipdiscovery.hpp','ipdiscovery.cpp',
                                   'codeobj.hpp','codeobj.cpp','offlinevalidation.hpp','offlinevalidation.cpp')]
    return {str(p.relative_to(ROOT)).replace('\\','/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

def run(args, name, data=None, timeout=30, expected_failure=False, environment=None):
    start=time.monotonic()
    p=subprocess.run([str(x) for x in args],cwd=ROOT,env=environment or ENV,input=data,
                     capture_output=True,text=True,encoding='utf-8',timeout=timeout)
    commands.append({'name':name,'argv':[str(x) for x in args],'exit':p.returncode,
                     'seconds':round(time.monotonic()-start,3),'expected_failure':expected_failure})
    log=OUT/(name+'.log')
    if log.exists():
        attempts=OUT/'attempts';attempts.mkdir(exist_ok=True)
        index=len(list(attempts.glob(name+'-*.log')))+1
        shutil.copyfile(log,attempts/(name+'-'+str(index)+'.log'))
    log.write_text(p.stdout+p.stderr,encoding='utf-8')
    if p.returncode and not expected_failure: raise RuntimeError(name+' failed; see '+str(OUT/(name+'.log')))
    if not p.returncode and expected_failure: raise RuntimeError(name+' failed to detect intentional fault')
    return p.stdout

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module
n=load('m65navi44',ROOT/'development/AMDRadeonRDNA4-Navi44/host/navi44.py')
f=load('m65fixtures',ROOT/'tests/fixtures/synthetic.py')

def build(source, output, sanitize=False):
    args=[CPP,'-std=c++17','-Wall','-Wextra','-Werror','-static','-g','-O1','-I'+str(SRC)]
    if sanitize: args += ['-fsanitize='+('address,undefined' if sanitize is True else sanitize),'-fno-omit-frame-pointer']
    args += [ROOT/source,SRC/'ipdiscovery.cpp',SRC/'offlinevalidation.cpp',SRC/'codeobj.cpp','-o',BUILD/output]
    run(args,'compile-'+Path(output).stem,timeout=60)
    return BUILD/output

def canonical(mode,data,params=()):
    try:
        if mode=='discovery':
            d=n.parse_discovery(data)
            return {'ok':True,'binary_version':list(d.binary_version),'ipds_version':d.ipds_version,
                    'address_bits':d.address_bits,'ips':[[x.hw_id,x.instance,*x.version,list(x.bases)] for x in d.ips],
                    'gc_info':list(d.gc_info) if d.gc_info else None}
        if mode=='elf':
            target={0x48:n.Target.GFX1200,0x4e:n.Target.GFX1201}.get(params[0],n.Target.UNKNOWN)
            n.validate_elf(data,target);return {'ok':True}
        if mode=='kernel':
            target={0x48:n.Target.GFX1200,0x4e:n.Target.GFX1201}.get(params[0],n.Target.UNKNOWN)
            n.validate_kernel(data,target);return {'ok':True}
        if mode=='manifest':
            d=n.parse_discovery(data);p=n.identify(0x1002,params[0])
            needs=n.firmware_requirements(p,d)
            return {'ok':True,'requirements':[[x.block,x.component,*x.ip] for x in needs]}
        if mode=='firmware':
            need=n.FirmwareNeed('synthetic',(params[0],params[1],0),params[2])
            n.validate_firmware([need],[n.FirmwareBlob(need,data,'synthetic')]);return {'ok':True}
        if mode=='abi':
            p=n.decode_device_info(data);return {'ok':True,'target':p.target.value,'capabilities':0}
        if mode=='profile':
            p=n.identify(params[0],params[1],None if params[2]==256 else params[2])
            return {'ok':True,'asic':p.asic,'target':p.target.value,'revision':p.revision,'capabilities':0}
        raise ValueError(mode)
    except n.Invalid as e:return {'ok':False,'error':str(e)}

def request(mode,data,params):
    tail='' if mode=='profile' else data.hex()
    return ' '.join([mode,*[str(x) for x in params],tail])+'\n'

def compare(exe,cases,name):
    text=run([exe],name,''.join(request(*c) for c in cases),timeout=30)
    rows=text.splitlines()
    if len(rows)!=len(cases):raise RuntimeError('Probe output count mismatch')
    differences=[]
    for i,(case,row) in enumerate(zip(cases,rows)):
        expected=canonical(*case); actual=json.loads(row)
        if expected!=actual:
            differences.append({'index':i,'mode':case[0],'params':case[2],
                                'hex':case[1].hex(),'python':expected,'cpp':actual})
    (OUT/(name+'-differences.json')).write_text(json.dumps(differences,indent=2),encoding='utf-8')
    if differences:raise RuntimeError(name+' differences: '+str(len(differences)))
    return len(cases)

def corpus():
    cases=[]
    for binary in (1,2):
        for width in (4,8):
            for gc in ((12,0,0),(12,0,1)):
                cases.append(('discovery',f.discovery(binary=binary,width=width,gc=gc),()))
    cases += [('discovery',f.discovery(width=8,extra=((999,0,(1,0,0),(0x100000000,)),)),()),
              ('discovery',f.discovery(topology=False),()),
              ('discovery',f.discovery(extra=((11,0,(12,0,0),(10,)),)),())]
    d=f.discovery()
    cases += [('discovery',d[:i],()) for i in range(len(d))]
    for offset,value,width in ((0,0,4),(4,9,2),(132,5,2),(144,1,2),(215,17,1),(128+12,2,2)):
        b=bytearray(d);struct.pack_into({1:'<B',2:'<H',4:'<I'}[width],b,offset,value)
        f.reseal(b);cases.append(('discovery',b,()))
    for target in (0x48,0x4e,0):
        cases += [('elf',f.elf(machine), (target,)) for machine in (0x48,0x4e)]
    cases += [('elf',f.elf()[:i],(0x48,)) for i in range(64)]
    cases += [('elf',f.elf(metadata=False),(0x48,)),('elf',f.elf(metadata_value={}),(0x48,))]
    for component in ('pfp','unknown'):
        need=n.FirmwareNeed('gc',(12,0,0),component)
        cases += [('firmware',f.firmware(need),(12,0,component))]
    need=n.FirmwareNeed('gc',(12,0,0),'pfp');fw=f.firmware(need)
    cases += [('firmware',fw[:i],(12,0,'pfp')) for i in range(len(fw))]
    for v,dv,rev in ((0x1002,0x7590,256),(0x1002,0x7550,0),(0x1002,0x7551,3),
                     (0x1002,0xffff,256),(0,0x7590,256),(0x1002,0x7590,257)):
        cases.append(('profile',b'',(v,dv,rev)))
    abi=n.encode_device_info(n.identify(0x1002,0x7590))
    cases += [('abi',abi[:i],()) for i in range(len(abi))]
    cases.append(('abi',abi,()))
    cases += [('kernel',f.kernel_elf(t),(t,)) for t in (0x48,0x4e)]
    for at,value,fmt in ((840,9,'<I'),(832,17,'<I'),(848,-0x2000,'<q'),(1060,0,'<B')):
        d=f.kernel_elf();struct.pack_into(fmt,d,at,value);cases.append(('kernel',d,(0x48,)))
    d=f.kernel_elf(0x4e);d[486]=230
    cases.append(('kernel',d,(0x4e,)))
    regression=ROOT/'tests/fixtures/m65-invalid-strtab.bin'
    if not regression.exists():regression.write_bytes(d)
    cases += [('manifest',f.discovery(gc=gc),(device,)) for gc,device in
              (((12,0,0),0x7590),((12,0,1),0x7550),((12,0,1),0x7590))]
    cases += [('manifest',f.discovery(topology=False),(0x7590,))]
    return cases

def fuzz_cases(count=2400):
    rng=random.Random(759065);base=corpus()
    seeds=[c for c in base if len(c[1])>=32 and c[0]!='profile']
    result=[]
    for i in range(count):
        mode,raw,params=rng.choice(seeds);data=bytearray(raw)
        for _ in range(rng.randrange(1,5)):data[rng.randrange(len(data))]^=rng.randrange(1,256)
        if mode=='discovery' and len(data)>=128 and i%2==0:
            # Reseal only structurally full images to exercise deeper branches.
            if len(data)==struct.unpack_from('<H',data,10)[0] and struct.unpack_from('<H',data,4)[0] in (1,2):
                f.reseal(data)
        result.append((mode,data,params))
    return result

def main():
    provenance=json.loads((ROOT/'reports/m65/toolchain-provenance.json').read_text(encoding='utf-8'))
    archive=ROOT/'tools/toolchains/llvm-mingw-20261006-ucrt-x86_64.zip'
    with archive.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    if digest!=provenance['expected_sha256']:raise RuntimeError('Toolchain archive digest changed')
    version=run([CPP,'--version'],'compiler-version')
    run([sys.executable,'-I','-B','-X','utf8',ROOT/'tests/test_offline.py'],'python-tests')
    run([sys.executable,'-I','-B','-X','utf8',ROOT/'tests/test_m65.py'],'python-m65-tests')
    py_log=(OUT/'python-tests.log').read_text(encoding='utf-8')
    extra_log=(OUT/'python-m65-tests.log').read_text(encoding='utf-8')
    py_counts=unittest_counts(py_log); extra_counts=unittest_counts(extra_log)
    unit=build('tests/unit/m65_unit.cpp','unit.exe');probe=build('tests/unit/m65_probe.cpp','probe.exe')
    unitlog=run([unit],'cpp-unit')
    cpp_pass=sum(line.startswith('PASS ') for line in unitlog.splitlines())
    analysis=[]
    for source in ('ipdiscovery.cpp','codeobj.cpp','offlinevalidation.cpp'):
        run([CPP,'--analyze','-std=c++17','-I'+str(SRC),SRC/source,
                  '-o',BUILD/(source+'.plist')],'static-analysis-'+source,timeout=30)
        log=(OUT/('static-analysis-'+source+'.log')).read_text(encoding='utf-8')
        analysis.append({'source':source,'warnings':len(re.findall(r'warning:',log)),'exit':0})
    fixtures=corpus()
    (OUT/'shared-corpus.json').write_text(json.dumps([{'mode':m,'hex':bytes(d).hex(),'params':p} for m,d,p in fixtures],indent=2),encoding='utf-8')
    diff=compare(probe,fixtures,'differential')
    fuzz=fuzz_cases();fuzz_count=compare(probe,fuzz,'fuzz-seed-759065')
    sanitizer={'status':'NOT RUN'}
    sanitized=build('tests/unit/m65_unit.cpp','unit-sanitized.exe',True)
    sp=build('tests/unit/m65_probe.cpp','probe-sanitized.exe',True)
    # ASan DLL imports libc++, which in turn imports libunwind. Copy the
    # verified portable runtime beside the executable, never into Windows.
    for name in ('libclang_rt.asan_dynamic-x86_64.dll','libc++.dll','libunwind.dll','libwinpthread-1.dll'):
        shutil.copyfile(BIN/name,BUILD/name)
    run([sanitized],'sanitized-unit')
    compare(sp,fixtures+fuzz,'sanitized-corpus')
    canaries={}
    for kind,diagnostic in (('address','heap-buffer-overflow'),('undefined','signed integer overflow')):
        exe=build('tests/unit/sanitizer_canary.cpp','canary-'+kind+'.exe',kind)
        mode='asan' if kind=='address' else 'ubsan'
        env=ENV.copy()
        if mode=='asan':
            env.pop('UBSAN_OPTIONS',None)
            env['ASAN_OPTIONS']='halt_on_error=1:detect_leaks=0:log_path=reports/m7/baseline/asan-canary'
        else:
            env.pop('ASAN_OPTIONS',None)
            env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1:log_path=reports/m7/baseline/ubsan-canary'
        previous=set(OUT.glob(mode+'-canary.*'))
        text=run([exe,mode],'canary-'+mode,expected_failure=True,environment=env)
        evidence=(OUT/('canary-'+mode+'.log')).read_text(encoding='utf-8')+text+'\n'.join(
            p.read_text(encoding='utf-8',errors='replace') for p in set(OUT.glob(mode+'-canary.*'))-previous)
        if diagnostic not in evidence:raise RuntimeError('Missing sanitizer canary diagnostic: '+mode)
        canaries[mode]='PASS: intentional CPU-only fault detected'
    sanitizer={'status':'PASS','flags':'address,undefined','unit_cases':cpp_pass,
               'corpus_cases':len(fixtures)+len(fuzz),'leak_detection':'disabled on Windows; NOT VERIFIED'}
    summary={'stage':'M6.5','status':'PASS',
             'completed_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),
             'compiler':version,'source_sha256':source_manifest(),
             'python':{'baseline_tests':py_counts['tests'],
                       'baseline_pass':py_counts['PASS'],'baseline_skip':py_counts['SKIP'],
                       'static_checks_in_baseline':py_counts['static_checks'],
                       'additional_tests':extra_counts['tests'],'FAIL':py_counts['FAIL']+extra_counts['FAIL'],
                       'baseline_detail':py_counts,'additional_detail':extra_counts},
             'static_analysis':analysis,'cpp_unit':{'PASS':cpp_pass,'FAIL':0},'differential':{'PASS':diff,'FAIL':0},
             'fuzz':{'seed':759065,'cases':fuzz_count,'status':'PASS','type':'bounded deterministic mutation; not coverage-guided'},
             'sanitizers':sanitizer,'sanitizer_canaries':canaries,'hardware':'NOT RUN','kext':'NOT RUN',
             'actual_gfx1200_elf':'SKIP: portable compiler has no AMDGPU backend'}
    (OUT/'results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('compiler','source_sha256')},indent=2))

previous_result=OUT/'results.json'
if previous_result.exists():
    attempts=OUT/'attempts';attempts.mkdir(exist_ok=True)
    index=len(list(attempts.glob('results-*.json')))+1
    shutil.copyfile(previous_result,attempts/('results-'+str(index)+'.json'))
previous_result.write_text(json.dumps({'stage':'M6.5','status':'RUNNING'},indent=2),encoding='utf-8')
try: main()
except Exception as exc:
    previous_result.write_text(json.dumps({'stage':'M6.5','status':'FAIL',
                                           'error':type(exc).__name__+': '+str(exc)},ensure_ascii=False,indent=2),encoding='utf-8')
    raise
finally:
    path=OUT/'commands.json'
    if path.exists():
        attempts=OUT/'attempts';attempts.mkdir(exist_ok=True)
        shutil.copyfile(path,attempts/('commands-'+str(len(list(attempts.glob('commands-*.json')))+1)+'.json'))
    path.write_text(json.dumps(commands,ensure_ascii=False,indent=2),encoding='utf-8')
