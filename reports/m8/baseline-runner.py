"""M7 project-checked CPU-only pipeline. No automatic downloads or hardware."""
from pathlib import Path
import hashlib,json,os,shutil,sys,time
sys.path.insert(0,'D:\\CodexWorkSpace\\黑苹果研究\\Hackintosh-Navi44-Lab')
import m7_safety as safe
ROOT=safe.ROOT;OUT=safe.mkdir('reports/m8/baseline/execution');BUILD=safe.mkdir('build/m8/baseline/execution')
safe.preflight(['tmp','run_all_offline_tests.py','tests/fixtures/m65-invalid-strtab.bin'])
# Reuse audited host test/corpus helpers, not its main/old-report writer.
original=(ROOT/'run_all_offline_tests.py').read_text(encoding='utf-8')
if original.count('previous_result=OUT/')!=1 or "OUT=ROOT/'reports/m65'; BUILD=ROOT/'build/m65'" not in original:
    raise RuntimeError('Reviewed historical helper boundary changed; refusing execution')
if not safe.checked('tests/fixtures/m65-invalid-strtab.bin').is_file():
    raise RuntimeError('Historical regression fixture missing; refusing implicit regeneration')
source=original.split('previous_result=OUT/')[0]
source=source.replace("OUT=ROOT/'reports/m65'; BUILD=ROOT/'build/m65'","OUT=ROOT/'reports/m8/baseline/execution'; BUILD=ROOT/'build/m8/baseline/execution'")
source=source.replace('log_path=reports/m65/','log_path=reports/m8/baseline/execution/')
b={'__file__':str(ROOT/'run_all_offline_tests.py'),'__name__':'m7helpers'};exec(compile(source,'m7-reviewed-host-helpers','exec'),b)
CPP=b['CPP'];SRC=b['SRC'];CORE=SRC.parent/'core';run_base=b['run'];old_canonical=b['canonical']
def archive(path):
    path=safe.checked(path)
    if path.exists():
        folder=safe.mkdir(OUT/'attempts')
        index=len(list(folder.glob(path.stem+'-*.'+path.suffix.lstrip('.'))))+1
        safe.write(folder/(path.stem+'-'+str(index)+path.suffix),path.read_bytes())

def run(args,name,data=None,timeout=30,expected_failure=False,environment=None):
    log=safe.checked(OUT/(name+'.log'));archive(log)
    safe.checked(BUILD);safe.checked(ROOT/'tmp')
    if '-o' in args:safe.checked(args[args.index('-o')+1])
    start=time.monotonic()
    try:
        p=b['subprocess'].run([str(x) for x in args],cwd=ROOT,env=environment or b['ENV'],input=data,
                              capture_output=True,text=True,encoding='utf-8',timeout=timeout)
    except b['subprocess'].TimeoutExpired as exc:
        b['commands'].append({'name':name,'argv':[str(x) for x in args],'exit':None,'status':'TIMEOUT',
                              'seconds':round(time.monotonic()-start,3)})
        safe.write(log,'TIMEOUT: '+str(exc));raise
    b['commands'].append({'name':name,'argv':[str(x) for x in args],'exit':p.returncode,
                          'seconds':round(time.monotonic()-start,3),'expected_failure':expected_failure})
    safe.write(log,p.stdout+p.stderr)
    if p.returncode and not expected_failure:raise RuntimeError(name+' failed; see '+str(log))
    if not p.returncode and expected_failure:raise RuntimeError(name+' failed to detect intentional fault')
    return p.stdout
b['run']=run
extra=b['load']('m7cases',ROOT/'tests/test_m7.py');n=b['n'];f=b['f']
def canonical(mode,data,params=()):
    try:
        if mode=='psp':
            p=n.parse_psp_package(data)
            return {'ok':True,'signature_verified':False,'parts':[[k,x['version'],x['offset'],x['size']] for k,x in sorted(p['parts'].items())]}
        if mode=='abi2':
            p=n.decode_device_info_v2(data);return {'ok':True,**{k:list(v) if isinstance(v,tuple) else v for k,v in p.items()}}
        if mode=='elfbudget':
            t={72:n.Target.GFX1200,78:n.Target.GFX1201}.get(params[0],n.Target.UNKNOWN)
            n.validate_elf(data,t,node_budget=params[1]);return {'ok':True}
        return old_canonical(mode,data,params)
    except n.Invalid as e:return {'ok':False,'error':str(e)}
b['canonical']=canonical

def compare(exe,cases,name):
    output=run([exe],name,''.join(b['request'](*c) for c in cases),timeout=30).splitlines()
    if len(output)!=len(cases):raise RuntimeError('Probe output count mismatch')
    differences=[]
    for i,(case,row) in enumerate(zip(cases,output)):
        expected=canonical(*case);actual=json.loads(row)
        if expected!=actual:
            differences.append({'index':i,'mode':case[0],'params':case[2],'hex':bytes(case[1]).hex(),
                                'python':expected,'cpp':actual})
    path=OUT/(name+'-differences.json');archive(path);safe.write(path,json.dumps(differences,indent=2))
    if differences:raise RuntimeError(name+' differences: '+str(len(differences)))
    return len(cases)
b['compare']=compare
def cases():
    result=b['corpus']()
    result += [('psp',extra.package(m),()) for m in (0,1)]
    result += [('psp',extra.package()[:i],()) for i in range(len(extra.package()))]
    for offset,value,fmt in ((52,1,'<I'),(60,2,'<I'),(10,9,'<H'),(28,1,'<I'),(64,0xffff,'<I')):
        data=extra.package();extra.struct.pack_into(fmt,data,offset,value);result.append(('psp',data,()))
    result += [('abi2',extra.abi2(device,present),()) for device in (0x7590,0x7550) for present in (0,1,2,4,7)]
    result += [('abi2',extra.abi2()[:i],()) for i in range(96)]
    for offset in (13,20,27,28,68,95):
        data=extra.abi2();data[offset]=3;result.append(('abi2',data,()))
    result += [('elfbudget',f.elf(),(72,budget)) for budget in (0,1,128)]
    for binary,off in ((1,18),(2,14)):
        data=f.discovery(binary=binary);data[off]=1;f.reseal(data);result.append(('discovery',data,()))
    result += [('elf',extra.relocation(allocated),(72,)) for allocated in (False,True)]
    for offset,value,fmt in ((1096,3<<32,'<Q'),(192+6*64+56,8,'<Q')):
        data=extra.relocation();extra.struct.pack_into(fmt,data,offset,value);result.append(('elf',data,(72,)))
    for offset,value,fmt in ((192+5*64+40,1,'<I'),(192+5*64+56,8,'<Q')):
        data=f.kernel_elf();extra.struct.pack_into(fmt,data,offset,value);result.append(('elf',data,(72,)))
    return result
all_cases=cases()
def fuzz_cases(count=2400):
    rng=b['random'].Random(759070);seeds=[x for x in all_cases if len(x[1])>=32 and x[0] not in ('profile','elfbudget')]
    result=[]
    for i in range(count):
        mode,data,params=rng.choice(seeds);data=bytearray(data)
        for _ in range(rng.randrange(1,5)):data[rng.randrange(len(data))]^=rng.randrange(1,256)
        if mode=='discovery' and len(data)>=128 and i%2==0:
            if len(data)==b['struct'].unpack_from('<H',data,10)[0] and b['struct'].unpack_from('<H',data,4)[0] in (1,2):f.reseal(data)
        result.append((mode,data,params))
    return result
def build(test,name,sanitize=False):
    objects=[]
    for p in (SRC/'ipdiscovery.cpp',SRC/'codeobj.cpp',CORE/'validation.cpp',CORE/'device_info.cpp'):
        obj=BUILD/(name+'-'+p.stem+'.o');safe.checked(obj)
        flags=[CPP,'-std=c++17','-Wall','-Wextra','-Werror','-fno-exceptions','-fno-rtti','-ffreestanding',
               '-Wframe-larger-than=4096','-g','-O1','-I'+str(SRC)]
        if sanitize:flags+=['-fsanitize='+('address,undefined' if sanitize is True else sanitize),'-fno-omit-frame-pointer']
        run(flags+['-c',p,'-o',obj],'compile-'+name+'-'+p.stem,timeout=40);objects.append(obj)
    # Audit pure Core undefined symbols; compatibility/stdio remain Host-only.
    forbidden=('__cxa_throw','__gxx_personality','_Unwind','__dynamic_cast','_ZSt','_Znwm','_Znam')
    for obj in objects:
        text=run([b['BIN']/'llvm-nm.exe','--undefined-only',obj],'symbols-'+obj.stem)
        if any(token in text for token in forbidden):raise RuntimeError('Host runtime dependency in Core object: '+str(obj))
    exe=BUILD/(name+'.exe');flags=[CPP,'-std=c++17','-Wall','-Wextra','-Werror','-static','-g','-O1','-I'+str(SRC)]
    if sanitize:flags+=['-fsanitize='+('address,undefined' if sanitize is True else sanitize),'-fno-omit-frame-pointer']
    run(flags+[ROOT/test,SRC/'offlinevalidation.cpp',*objects,'-o',exe],'link-'+name,timeout=40)
    return exe
def main():
    archive=ROOT/'tools/toolchains/llvm-mingw-20261006-ucrt-x86_64.zip'
    expected=json.loads((ROOT/'reports/m65/toolchain-provenance.json').read_text())['expected_sha256']
    with archive.open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest()!=expected:raise RuntimeError('Archive integrity failure')
    run([CPP,'--version'],'compiler-version')
    python={}
    for file in ('test_offline.py','test_m65.py','test_m7.py'):
        run([sys.executable,'-I','-B','-X','utf8',ROOT/'tests'/file],'python-'+file)
        python[file]=b['unittest_counts']((OUT/('python-'+file+'.log')).read_text())
    old=build('tests/unit/m65_unit.cpp','regression-unit');new=build('tests/unit/m7_unit.cpp','m7-unit');probe=build('tests/unit/m65_probe.cpp','probe')
    old_log=run([old],'regression-unit');new_log=run([new],'m7-unit')
    diff=b['compare'](probe,all_cases,'differential');fuzz=fuzz_cases();fuzz_count=b['compare'](probe,fuzz,'fuzz')
    sanitized=build('tests/unit/m7_unit.cpp','m7-sanitized',True);sp=build('tests/unit/m65_probe.cpp','probe-sanitized',True)
    for file in ('libclang_rt.asan_dynamic-x86_64.dll','libc++.dll','libunwind.dll','libwinpthread-1.dll'):
        safe.write(BUILD/file,(b['BIN']/file).read_bytes())
    run([sanitized],'sanitized-m7-unit');b['compare'](sp,all_cases+fuzz,'sanitized-corpus')
    canaries={}
    for kind,diagnostic in (('address','heap-buffer-overflow'),('undefined','signed integer overflow')):
        exe=build('tests/unit/sanitizer_canary.cpp','canary-'+kind,kind);mode='asan' if kind=='address' else 'ubsan'
        env=b['ENV'].copy();env.pop('UBSAN_OPTIONS' if mode=='asan' else 'ASAN_OPTIONS',None)
        env['ASAN_OPTIONS' if mode=='asan' else 'UBSAN_OPTIONS']='halt_on_error=1:log_path=reports/m8/baseline/execution/'+mode+'-canary'
        before=set(OUT.glob(mode+'-canary.*'));run([exe,mode],'canary-'+mode,expected_failure=True,environment=env)
        evidence=(OUT/('canary-'+mode+'.log')).read_text()+'\n'.join(p.read_text(errors='replace') for p in set(OUT.glob(mode+'-canary.*'))-before)
        if diagnostic not in evidence:raise RuntimeError('Canary failed: '+mode)
        canaries[mode]='PASS'
    analysis=[]
    for file in (CORE/'validation.cpp',CORE/'device_info.cpp',SRC/'ipdiscovery.cpp',SRC/'codeobj.cpp'):
        run([CPP,'--analyze','-std=c++17','-fno-exceptions','-fno-rtti','-I'+str(SRC),file,'-o',BUILD/(file.stem+'.plist')],'analyze-'+file.stem,timeout=30)
        text=(OUT/('analyze-'+file.stem+'.log')).read_text();analysis.append({'source':file.name,'warnings':text.count('warning:')})
    result={'stage':'M7','status':'PASS','completed_at':b['datetime'].now(b['timezone'](b['timedelta'](hours=8))).isoformat(),
            'python':python,'cpp_regression':old_log.count('PASS '),'cpp_m7':new_log.count('PASS '),
            'differential':diff,'fuzz':{'seed':759070,'inputs':fuzz_count,'coverage_guided':False},
            'core_compile':'PASS: no-exceptions/no-rtti/freestanding + object symbol audit',
            'sanitizers':{'status':'PASS','inputs':len(all_cases)+len(fuzz),'canaries':canaries,'leak_detection':'NOT VERIFIED'},
            'static_analysis':analysis,'kext':'NOT RUN','GPU':'NOT RUN','real_gfx1200_ELF':'SKIP'}
    safe.write('reports/m8/baseline/test-results.json',json.dumps(result,indent=2));print(json.dumps(result,indent=2))
for prior in ('test-results.json','commands.json'):
    archive(ROOT/'reports/m7'/prior)
try:main()
except Exception as exc:
    safe.write('reports/m8/baseline/test-results.json',json.dumps({'stage':'M7','status':'FAIL','error':str(exc)},indent=2));raise
finally:safe.write('reports/m8/baseline/commands.json',json.dumps(b['commands'],ensure_ascii=False,indent=2))
