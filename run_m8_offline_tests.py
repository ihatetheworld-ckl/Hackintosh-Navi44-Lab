"""Reviewed serial CPU-only M8 pipeline. No install, hardware APIs or SDK fakery."""
from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m7_safety as safe
ROOT=safe.ROOT;OUT=safe.mkdir('reports/m8');BUILD=safe.mkdir('build/m8/execution')
# Import reviewed M7 definitions only, redirect all its reports before any execution.
text=(ROOT/'run_m7_offline_tests.py').read_text()
if text.count("for prior in ('test-results.json','commands.json'):")!=1:raise SystemExit('M7 helper boundary changed')
text=text.split("for prior in ('test-results.json','commands.json'):")[0]
text=text.replace('reports/m7/','reports/m8/regression/').replace('build/m7/','build/m8/regression/')
r={'__file__':str(ROOT/'run_m7_offline_tests.py'),'__name__':'m8_reviewed_helpers'}
exec(compile(text,'reviewed-M7-host-helpers','exec'),r)
# Keep new-stage log/build records separate from M7 regression.
run=r['run'];commands=r['b']['commands'];CPP=r['CPP'];SRC=r['SRC'];CORE=r['CORE']
sources=[SRC/'ipdiscovery.cpp',SRC/'codeobj.cpp',CORE/'validation.cpp',CORE/'device_info.cpp',
         SRC/'edid.cpp',SRC/'atombios.cpp',CORE/'display.cpp',CORE/'integrity.cpp',CORE/'query_candidate.cpp']
objects={}
def build(test,name,sanitize=False):
    key='asan-ubsan' if sanitize else 'plain'
    if key not in objects:
        objs=[]
        for p in sources:
            obj=safe.checked(BUILD/(key+'-'+p.stem+'.o'))
            args=[CPP,'-std=c++17','-Wall','-Wextra','-Werror','-fno-exceptions','-fno-rtti','-ffreestanding',
                  '-Wframe-larger-than=4096','-O1','-g','-I'+str(SRC)]
            if sanitize:args+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
            run(args+['-c',p,'-o',obj],'m8-compile-'+key+'-'+p.stem,timeout=40)
            symbols=run([r['b']['BIN']/'llvm-nm.exe','--undefined-only',obj],'m8-symbols-'+key+'-'+p.stem)
            if any(t in symbols for t in ('__cxa_throw','__gxx_personality','_Unwind','__dynamic_cast','_ZSt','_Znwm','_Znam')):
                raise RuntimeError('Core runtime dependency '+str(p))
            objs.append(obj)
        objects[key]=objs
    exe=safe.checked(BUILD/(name+'.exe'));args=[CPP,'-std=c++17','-Wall','-Wextra','-Werror','-static','-O1','-g','-I'+str(SRC)]
    if sanitize:args+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
    run(args+[ROOT/test,*objects[key],'-o',exe],'m8-link-'+name,timeout=40);return exe
def main():
    r['main']() # Actual M7 regression into M8 directory; never the original report writer.
    run([sys.executable,'-I','-B','-X','utf8',ROOT/'tests/test_m8.py'],'m8-python')
    extra_cases=[]
    raw=r['f'].elf()
    r['b']['struct'].pack_into('<H',raw,56,5000);extra_cases.append(('elf',raw,(72,)))
    # Input-budget is tested separately in each language: the existing Host
    # hex transport correctly refuses payloads above 1 MiB, before Core.
    reg_probe=ROOT/'build/m8/regression/execution/probe.exe'
    budget_diff=r['compare'](reg_probe,extra_cases,'m8-budget-differential')
    for filename in ('libclang_rt.asan_dynamic-x86_64.dll','libc++.dll','libunwind.dll','libwinpthread-1.dll'):
        safe.write(BUILD/filename,(r['b']['BIN']/filename).read_bytes())
    unit=build('tests/unit/m8_unit.cpp','m8-unit');fuzz=build('tests/unit/m8_fuzz.cpp','m8-fuzz')
    unitlog=run([unit],'m8-unit');fuzzlog=run([fuzz],'m8-fuzz')
    su=build('tests/unit/m8_unit.cpp','m8-unit-sanitized',True);sf=build('tests/unit/m8_fuzz.cpp','m8-fuzz-sanitized',True)
    run([su],'m8-unit-sanitized');run([sf],'m8-fuzz-sanitized')
    obj=BUILD/'contract-check.o'
    run([CPP,'-std=c++17','-Wall','-Wextra','-Werror','-fno-exceptions','-fno-rtti','-ffreestanding',
         '-Wframe-larger-than=4096','-I'+str(SRC),'-c',ROOT/'tests/unit/m8_contract_compile.cpp','-o',obj],
        'm8-contract-check',timeout=30)
    analysis=[]
    for p in sources+[ROOT/'tests/unit/m8_contract_compile.cpp']:
        run([CPP,'--analyze','-std=c++17','-fno-exceptions','-fno-rtti','-I'+str(SRC),p,'-o',BUILD/(p.stem+'.plist')],
            'm8-analyze-'+p.stem,timeout=30)
        log=(ROOT/'reports/m8/regression/execution'/('m8-analyze-'+p.stem+'.log')).read_text()
        analysis.append({'file':p.relative_to(ROOT).as_posix(),'warnings':log.count('warning:')})
    reg=json.loads((OUT/'regression/test-results.json').read_text())
    result={'stage':'M8','status':'PASS','regression':reg,'m8_cpp':unitlog.count('PASS '),'m8_fuzz':fuzzlog.strip(),
            'python_m8':r['b']['unittest_counts']((ROOT/'reports/m8/regression/execution/m8-python.log').read_text()),
            'budget_differential':budget_diff,
            'sanitizers':{'status':'PASS','unit_cases':unitlog.count('PASS '),'display_mutation_inputs':2400,'query_mutation_inputs':800,'leaks':'NOT VERIFIED'},
            'static_analysis':analysis,'kernel_contract_compile':'PASS','Darwin_native':'NOT RUN','Kext':'NOT RUN',
            'GPU':'NOT RUN','real_Navi44_ROM':'UNVERIFIED','real_monitor_EDID':'NOT READ'}
    safe.write(OUT/'test-results.json',json.dumps(result,indent=2));print(json.dumps(result,indent=2))
for rel in ('test-results.json','commands.json'):
    r['archive'](OUT/rel)
try:main()
except Exception as exc:
    safe.write(OUT/'test-results.json',json.dumps({'stage':'M8','status':'FAIL','error':str(exc)},indent=2));raise
finally:safe.write(OUT/'commands.json',json.dumps(commands,ensure_ascii=False,indent=2))
