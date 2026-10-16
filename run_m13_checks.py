"""Explicit M13 CPU, kernel object, policy and offline construction checks.

BSD-3-Clause. Existing Apple tools only. No downloads, bundle, signing, installation,
native execution, registration, device or GPU targets. SDK26.5 declarations are
checked separately from source exports and missing target-kernel binary evidence.
"""
import argparse,hashlib,json,os,platform,re,resource,shlex,struct,subprocess,sys,time
from pathlib import Path
if sys.version_info<(3,11):raise SystemExit('Existing Python 3.11+ required')
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m7_safety as safe
import run_m11_checks as previous
import m12_macho_audit as policy
import m13_target as target
P=previous.P
MODELS=[P.parent/'core/displayid.cpp',P.parent/'core/driver_model.cpp',P/'resource_model.cpp']
NATIVE=[*previous.NATIVE,P/'darwin_gate.cpp',safe.ROOT/'tests/unit/m12_native_compile.cpp',*MODELS]
IMPORTS={'_IOFreeAligned','_IOLog','_IOMallocAligned','__ZN24IOBufferMemoryDescriptor9withBytesEPKvmjb',
    '__ZN6OSData9withBytesEPKvj','__ZTV9IOService','_memcpy','_IORecursiveLockLock',
    '_IORecursiveLockUnlock','_IORecursiveLockHaveLock','_ml_at_interrupt_context','_ml_get_interrupts_enabled'}
PIN=target.PROFILE['xnu_pin']
def dependency_hook(script,variable):
    pattern=r'(?m)^( +)'+variable+r'\s*=\s*\[str\(x\) for x in '+variable+r'\]$'
    def change(m):
        indent=m[1];v=variable
        return m[0]+'\n'+indent+f"if {v}[0]==str(compiler) and '-o' in {v} and '-MD' not in {v} and any(x.endswith('.cpp') for x in {v}):\n"+indent+f"    {v}+=['-MD','-MF',str(safe.checked(build/(name+'-headers.d')))]"
    value,n=re.subn(pattern,change,script);assert n==1,'Reviewed dependency-hook boundary changed';return value
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--compiler',required=True);ap.add_argument('--sdk',required=True)
    ap.add_argument('--target',required=True,choices=['host','native','all'])
    ap.add_argument('--export-reference');ap.add_argument('--negative-sdk',help='Existing genuine SDK27 for isolated negative calibration; never downloaded');args=ap.parse_args()
    if sys.platform!='darwin' or platform.machine()!='arm64':raise SystemExit('Authorized arm64 macOS Host required')
    compiler=Path(args.compiler);sdk=Path(args.sdk)
    if not compiler.is_absolute() or not compiler.is_file() or not sdk.is_absolute() or not sdk.is_dir():raise ValueError('Existing tool/SDK required')
    out=safe.mkdir('reports/m13');local=safe.mkdir(out/'local/checks');build=safe.mkdir('build/m13/checks');tmp=safe.mkdir('tmp/m13/checks')
    env=os.environ.copy();env.update(TMPDIR=str(tmp),TMP=str(tmp),TEMP=str(tmp),CLANG_MODULE_CACHE_PATH=str(safe.mkdir(build/'cache')),
        PYTHONDONTWRITEBYTECODE='1',ASAN_OPTIONS='halt_on_error=1:detect_leaks=0:abort_on_error=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',TSAN_OPTIONS='halt_on_error=1')
    for k in ('CPATH','CPLUS_INCLUDE_PATH','C_INCLUDE_PATH','LIBRARY_PATH','DYLD_INSERT_LIBRARIES','SDKROOT','MACOSX_DEPLOYMENT_TARGET'):env.pop(k,None)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));commands=[]
    def public(x):
        if isinstance(x,Path):return public(str(x))
        if isinstance(x,str):return x.replace(str(safe.ROOT),'PROJECT_ROOT').replace(str(sdk),'SDK_ROOT').replace(sys.executable,'PYTHON_EXECUTABLE')
        if isinstance(x,list):return [public(v) for v in x]
        if isinstance(x,dict):return {public(k):public(v) for k,v in x.items()}
        return x
    def save(name,data):safe.write(out/(name+'.json'),json.dumps(public(data),indent=2,ensure_ascii=False))
    def run(cmd,name,timeout=60,allow=False):
        cmd=[str(x) for x in cmd]
        if cmd[0]==str(compiler) and '-o' in cmd and '-MD' not in cmd and any(x.endswith('.cpp') for x in cmd):
            cmd+=['-MD','-MF',str(safe.checked(local/(name+'-headers.d')))]
        for opt in ('-o','-MF'):
            if opt in cmd:safe.checked(cmd[cmd.index(opt)+1])
        print(name,flush=True);begin=time.monotonic()
        try:r=subprocess.run(cmd,cwd=safe.ROOT,env=env,text=True,capture_output=True,timeout=timeout)
        except subprocess.TimeoutExpired as e:
            safe.write(local/(name+'.log'),'TIMEOUT\n'+str(e.stdout)+str(e.stderr));commands.append(dict(name=name,status='TIMEOUT',argv=cmd));save('commands',commands);raise
        safe.write(local/(name+'.log'),r.stdout+r.stderr)
        commands.append(dict(name=name,argv=cmd,exit=r.returncode,seconds=round(time.monotonic()-begin,3)))
        safe.write(local/'commands-raw.json',json.dumps(commands,indent=2));save('commands',commands)
        if r.returncode and not allow:raise RuntimeError(name+' failed; raw log retained')
        return r
    source_files=set(NATIVE+[safe.ROOT/'tests/unit/m12_lifecycle.cpp',safe.ROOT/'tests/unit/m13_ioservice_layout.cpp',safe.ROOT/'tests/unit/m13_models.cpp',safe.ROOT/'tests/unit/m13_negative.cpp',safe.ROOT/'tests/unit/m12_policy_negative.cpp',Path(__file__),safe.ROOT/'m12_macho_audit.py',safe.ROOT/'m13_target.py',safe.ROOT/'config/m13-target.json'])
    source_files.update(P.glob('*.hpp'))
    source_files.update(P.parent.joinpath('core').glob('*.hpp'))
    source_files.update(P.parent.joinpath('src').glob('*.hpp'))
    source_files.update(safe.ROOT.joinpath('tests/unit').glob('*.cpp'))
    source_files.update([safe.ROOT/'run_host_tests.py',safe.ROOT/'run_m11_checks.py'])
    hashes={p.relative_to(safe.ROOT).as_posix():hashlib.sha256(safe.checked(p).read_bytes()).hexdigest() for p in source_files}
    save('executed-source-sha256',hashes)
    summary=dict(stage='M13',status='RUNNING',CPU_Host_Build='NOT RUN',Kernel_Object_Compile='NOT RUN',Partial_Link='NOT RUN',
        MH_KEXT_BUNDLE_Construction='NOT RUN',KPI_Reference_Audit='NOT RUN',Target_ABI_Compatibility='BLOCKED: target26.5 kernel binary/KDK absent',
        Full_Target_Link_Closure='BLOCKED',Bundle='NOT RUN',Sign='NOT RUN',Install='NOT RUN',Load='NOT RUN',Kernel_Runtime='NOT RUN',GPU_Runtime='NOT RUN',Windows_Regression='NOT RUN',x86_64_Runtime='NOT RUN')
    try:
        version=run([compiler,'--version'],'compiler-version').stdout
        if 'Apple clang' not in version:raise ValueError('Apple compiler required')
        tools={n:run(['xcrun','--find',n],'find-'+n).stdout.strip() for n in ('ld','nm','otool','lipo','dwarfdump')}
        linker=run([tools['ld'],'-v'],'linker-version');osver=run(['sw_vers'],'macos-version');xcode=run(['xcodebuild','-version'],'xcode-version')
        sdk_audit=target.sdk_info(sdk);save('sdk-audit',sdk_audit);sdkver=sdk_audit['version']
        resource_dir=run([compiler,'-print-resource-dir'],'compiler-resource-dir').stdout.strip()
        save('environment',dict(compiler=version,linker=linker.stdout+linker.stderr,macOS=osver.stdout,Xcode=xcode.stdout,SDK=str(sdk),SDK_version=sdkver,
            Python=sys.version,Host=platform.machine(),target='macOS 26.5 x86_64 / XNU 12377.121.6',XNU_pin=PIN,matched_SDK='SDK26.5 declarations verified; target binary UNVERIFIED',deployment_label_only=True))
        base=[compiler,'-std=c++17','-Wall','-Wextra','-Werror','-UNDEBUG','-O1','-g','-isysroot',sdk,'-mmacosx-version-min=26.5','-I'+str(previous.host.SRC)]
        cpu=['-fno-exceptions','-fno-rtti','-ffreestanding','-Wframe-larger-than=4096']
        if args.target in ('host','all'):
            # Reviewed existing runner; only redirect outputs and import root.
            helper=safe.checked('run_m11_checks.py').read_text().replace('-mmacosx-version-min=15.0','-mmacosx-version-min=26.5')
            helper=helper.replace('original=safe.checked("run_host_tests.py").read_text()', 'original=safe.checked("run_host_tests.py").read_text().replace("-mmacosx-version-min=13.0","-mmacosx-version-min=26.5")')
            helper=helper.replace('import run_host_tests as host','import run_host_tests as host\nfrom run_m13_checks import dependency_hook')
            helper=helper.replace('helper=original.replace(', 'original=dependency_hook(original,"command")\n            helper=original.replace(')
            helper=dependency_hook(helper,'cmd')
            for old,new in [('reports/m11','reports/m13/regression'),('build/m11','build/m13/regression'),('tmp/m11','tmp/m13/regression')]:helper=helper.replace(old,new)
            old='sys.path.insert(0,str(Path(__file__).resolve().parent))'
            if helper.count(old)!=1:raise ValueError('Reviewed import boundary changed')
            helper=helper.replace(old,'sys.path.insert(0,'+repr(str(safe.ROOT))+')')
            helper_path=safe.write(build/'reviewed-regression.py',helper)
            run([sys.executable,'-I','-B','-X','utf8',helper_path,'--compiler',compiler,'--sdk',sdk,'--target','host'],'legacy-regression',timeout=600)
            prior=json.loads(safe.checked('reports/m13/regression/test-results.json').read_text())
            if prior['status']!='PASS':raise ValueError('Legacy regression failed')
            behavior={}
            for mode,opts in [('normal',[]),('asan-ubsan',['-fsanitize=address,undefined','-fno-omit-frame-pointer']),('tsan',['-fsanitize=thread','-fno-omit-frame-pointer'])]:
                exe=build/(mode+'-m13-lifecycle')
                core_objects=[]
                for src in [P/'lifecycle.cpp',P/'shutdown.cpp']:
                    obj=build/(mode+'-'+src.stem+'.o')
                    run(base+['-arch','arm64',*cpu,*opts,'-c',src,'-o',obj],mode+'-m13-core-'+src.stem);core_objects.append(obj)
                run(base+['-arch','arm64',*opts,safe.ROOT/'tests/unit/m12_lifecycle.cpp',*core_objects,'-o',exe],mode+'-m13-build')
                log=run([exe],mode+'-m13-run',timeout=30).stdout;m=re.search(r'SUMMARY (\d+) (\d+)',log)
                if not m or int(m[2]) or 'FAIL ' in log:raise ValueError('M13 behavior failure')
                behavior[mode]=dict(PASS=int(m[1]),FAIL=int(m[2]),error_callbacks=300,concurrent_scopes=1,post_stop_attempts=160)
            new_behavior={}
            for mode,opts in [('normal',[]),('asan-ubsan',['-fsanitize=address,undefined','-fno-omit-frame-pointer']),('tsan',['-fsanitize=thread','-fno-omit-frame-pointer'])]:
                model_objects=[]
                for src in MODELS:
                    obj=build/(mode+'-'+src.stem+'.o');run(base+['-arch','arm64',*cpu,*opts,'-c',src,'-o',obj],mode+'-model-'+src.stem);model_objects.append(obj)
                parser_folder=safe.ROOT/'build/m13/regression/checks/host'/('m9-sanitized' if mode=='asan-ubsan' else 'm9-arm64')
                parser_objects=[parser_folder/(p.stem+'.o') for p in previous.host.PURE]
                exe=build/(mode+'-m13-models')
                run(base+['-arch','arm64',*opts,safe.ROOT/'tests/unit/m13_models.cpp',*model_objects,*parser_objects,build/(mode+'-lifecycle.o'),build/(mode+'-shutdown.o'),'-o',exe],mode+'-models-build')
                result=run([exe],mode+'-models-run',timeout=30);m=re.search(r'SUMMARY (\d+) (\d+)',result.stdout)
                if not m or int(m[2]):raise ValueError('M13 models behavior failed')
                new_behavior[mode]=dict(PASS=int(m[1]),FAIL=int(m[2]),bounded_DisplayID_mutations=500,seed=759013)
            summary.update(CPU_Host_Build='PASS',M12_regression_behavior=behavior,M13_behavior=new_behavior,legacy_regression='PASS',ASan_UBSan='PASS; leak detection not verified',TSan='PASS covered Host paths only')
            save('build-results',dict(legacy=prior,M12=behavior,M13=new_behavior))
        if args.target in ('native','all'):
            if not args.export_reference:raise ValueError('Explicit pinned reference files required')
            ref=json.loads(safe.checked(args.export_reference).read_text());target.reference(ref);additional=dict(files=[])
            exports_by_arch={};reference_files=[]
            for arch in ('x86_64','arm64'):
                exports={}
                for f in [*ref['files'],*additional['files']]:
                    if not f['path'].startswith('config/') or ('.x86_64.' in f['path'] and arch!='x86_64') or ('.arm64.' in f['path'] and arch!='arm64'):continue
                    sha=hashlib.sha256(f['text'].encode()).hexdigest()
                    if 'sha256' in f and f['sha256']!=sha:raise ValueError('Reference hash mismatch')
                    reference_files.append(dict(path=f['path'],sha256=sha,arch=arch))
                    for line in f['text'].splitlines():
                        line=line.strip()
                        if line.startswith('_'):exports[line.split()[0].split(':')[0]]=dict(file=f['path'],entry=line,sha256=sha,pin=PIN)
                exports_by_arch[arch]=exports
            kernel=sdk/'System/Library/Frameworks/Kernel.framework/Headers';native={};audits={};links={};layouts={};abi={};negatives=[]
            def image(path,arch,kind=1):
                data=policy.inspect(safe.checked(path).read_bytes(),arch,kind)
                if kind==1:target.object_target(data)
                data['path']=path.relative_to(safe.ROOT).as_posix();return data
            for arch in ('x86_64','arm64'):
                folder=safe.mkdir(build/('darwin-'+arch));objects=[];metadata=[];deps={}
                flags=base+['-arch',arch,*cpu,'-isystem',kernel,'-nostdinc++','-DKERNEL','-DKERNEL_EXTENSION','-mkernel','-fapple-kext','-fno-stack-protector']
                if arch=='x86_64':flags+=['-mno-red-zone']
                allowed=IMPORTS|({'___bzero'} if arch=='x86_64' else set())
                for src in NATIVE:
                    obj=folder/(src.stem+'.o');dep=folder/(src.stem+'.d')
                    run(flags+['-MD','-MF',dep,'-c',src,'-o',obj],arch+'-compile-'+src.stem);objects.append(obj)
                    metadata.append(dict(source=src.relative_to(safe.ROOT).as_posix(),flags=[str(x) for x in flags],image=image(obj,arch)))
                    for path in shlex.split(dep.read_text().replace('\\\n',''))[1:]:
                        p=Path(path)
                        category=target.dependency(p,sdk,resource_dir)
                        deps[str(p)]=dict(category=category,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                audit=policy.audit(metadata,{x['source'] for x in metadata},allowed,exports_by_arch[arch]);audits[arch]=audit
                if audit['status']!='PASS':save('symbol-audit',audits);raise ValueError('Independent symbol policy rejected '+arch)
                combined=folder/'n44-partial.o'
                run([tools['ld'],'-r','-arch',arch,'-platform_version','macos','26.5',sdkver,'-o',combined,*objects],arch+'-partial-link')
                part=image(combined,arch);remaining=sorted(s['name'] for s in part['symbols'] if s['undefined'])
                internal={s['name'] for x in metadata for s in x['image']['symbols'] if s['external'] and not s['undefined']}
                if any(s in internal or s not in allowed for s in remaining):raise ValueError('Combined symbol closure changed')
                nm=run([tools['nm'],'-u',combined],arch+'-partial-nm').stdout.splitlines()
                if sorted(nm)!=remaining:raise ValueError('Parser and Apple nm disagree')
                for name,opts in [('file',[]),('lipo',['-archs']),('otool',['-h','-l','-r']),('dwarfdump',['--verify'])]:run(['file' if name=='file' else tools[name],*opts,combined],arch+'-partial-'+name)
                native[arch]=dict(status='PASS',objects=metadata,flags=flags,header_sha256=deps)
                links[arch]=dict(Partial_Link='PASS',partial_artifact=part,remaining=remaining)
                abi[arch]=dict(current_SDK_object_options='PASS',target_SDK_match='SDK26.5 declarations verified',target_binary_exports='UNVERIFIED',target_vtable='UNVERIFIED',Kernel_Runtime='NOT RUN')
                layout=folder/'ioservice-layout.o'
                dump=run(flags+['-Xclang','-fdump-record-layouts','-Xclang','-fdump-vtable-layouts','-c',safe.ROOT/'tests/unit/m13_ioservice_layout.cpp','-o',layout],arch+'-layout-compile')
                li=image(layout,arch);sizes={};raw=layout.read_bytes()
                for s in li['symbols']:
                    if s['name'].startswith(('_n44_size_','_n44_align_')):
                        section=li['sections'][s['section']-1];sizes[s['name']]=struct.unpack_from('<Q',raw,section['offset']+s['value']-section['address'])[0]
                layouts[arch]=dict(current_SDK=sdkver,sizes=sizes,artifact_sha256=li['sha256'],layout_log=str(local/(arch+'-layout-compile.log')),target_binary_layout='UNVERIFIED',excluded_from_link=True)
                if arch=='x86_64':
                    linked=folder/'n44-offline.macho'
                    r=run([tools['ld'],'-kext','-arch',arch,'-platform_version','macos','26.5',sdkver,'-undefined','error','-o',linked,combined],arch+'-kext-construction',allow=True)
                    links[arch].update(Linker_exit=r.returncode,Full_Target_Link_Closure='BLOCKED',Bundle='NOT RUN',Sign='NOT RUN',Install='NOT RUN',Load='NOT RUN')
                    if r.returncode:raise ValueError('Offline construction failed')
                    final=image(linked,arch,11)
                    if sorted(s['name'] for s in final['symbols'] if s['undefined'])!=remaining:raise ValueError('Image import set changed')
                    run([tools['otool'],'-h','-l','-r',linked],'x86_64-image-otool');run([tools['nm'],'-u',linked],'x86_64-image-nm')
                    run([tools['otool'],'-tvV',folder/'m11_native_compile.o'],'x86_64-service-disassembly')
                    links[arch].update(MH_KEXT_BUNDLE_Construction='PASS',image=final)
                    fixture=safe.ROOT/'tests/unit/m12_policy_negative.cpp';badfolder=safe.mkdir(build/'negative');srcname=fixture.relative_to(safe.ROOT).as_posix()
                    for mode,reason in [('HOST','HOST_RUNTIME'),('UNKNOWN','UNKNOWN_IMPORT'),('EXCEPTION','EXCEPTION_RUNTIME'),('RTTI','RTTI_RUNTIME'),('PRINTF','UNSUPPORTED_KERNEL_IMPORT'),('INITIALIZER','initializer_eh_or_tls')]:
                        bad=badfolder/(mode.lower()+'.o')
                        opts=flags if mode in ('UNKNOWN','PRINTF','INITIALIZER') else base+['-arch',arch,'-fno-stack-protector','-fno-unwind-tables','-fno-asynchronous-unwind-tables']
                        run(opts+['-DN44_POLICY_'+mode,'-c',fixture,'-o',bad],'negative-compile-'+mode)
                        # Actual Apple symbols provide diagnostics even when unsafe sections reject first.
                        symbols=run([tools['nm'],'-u',bad],'negative-symbols-'+mode).stdout.splitlines()
                        found=[]
                        try:
                            item=dict(source=srcname,flags=[str(x) for x in opts],image=image(bad,arch))
                            pa=policy.audit([item],{srcname},allowed,exports_by_arch[arch]);found=[x['reason'] for x in pa['errors']]
                        except policy.AuditError as e:found.append(str(e))
                        if reason not in found and reason in ('EXCEPTION_RUNTIME','RTTI_RUNTIME'):
                            found.extend(filter(None,(policy.runtime_reason(s) for s in symbols)))
                        if reason not in found:raise ValueError('Negative case not detected: '+mode+str(found))
                        record=dict(case=mode,status='REJECTED',expected_reason=reason,reasons=found,symbols=symbols,sha256=hashlib.sha256(bad.read_bytes()).hexdigest(),never_executed=True)
                        if mode=='HOST':
                            invalid=badfolder/'invalid-kext.macho'
                            nr=run([tools['ld'],'-kext','-arch',arch,'-undefined','error','-o',invalid,combined,bad],'negative-linker-calibration',allow=True)
                            record.update(linker_exit=nr.returncode,independent_policy_required=True)
                        negatives.append(record)
                    provider=badfolder/'provider.o';consumer=badfolder/'consumer.o';testobjs=[]
                    for mode,dest in [('PROVIDER',provider),('CONSUMER',consumer)]:
                        run(flags+['-DN44_POLICY_'+mode,'-c',fixture,'-o',dest],'negative-compile-'+mode)
                        testobjs.append(dict(source=srcname,flags=[str(x) for x in flags],image=image(dest,arch)))
                    wrong=policy.audit(testobjs,{srcname},allowed,exports_by_arch[arch],{'_n44_policy_required':{'expected/project/provider.cpp'}})
                    if 'WRONG_SYMBOL_PROVIDER' not in [x['reason'] for x in wrong['errors']]:raise ValueError('Wrong provider accepted')
                    negatives.append(dict(case='WRONG_PROVIDER',status='REJECTED',errors=wrong['errors'],fake_Apple_API=False))
                    # Malformed copies are mutations of genuine objects, never forged headers or executable fixtures.
                    valid=objects[0].read_bytes();v=image(objects[0],arch)
                    for mode in ('STRING_INDEX','RELOCATION_INDEX'):
                        raw=bytearray(valid);pos=32;so=None
                        for command in v['commands']:
                            if command['command']==2:so=struct.unpack_from('<I',raw,pos+8)[0]
                            pos+=command['bytes']
                        if mode=='STRING_INDEX':struct.pack_into('<I',raw,so,0xffffffff)
                        else:
                            section=next(x for x in v['sections'] if x['nreloc']);at=section['reloff']+4;word=struct.unpack_from('<I',raw,at)[0]
                            struct.pack_into('<I',raw,at,(word&0xf0000000)|(1<<27)|0xffffff)
                        try:policy.inspect(raw,arch);raise ValueError('Malformed negative accepted')
                        except policy.AuditError as e:negatives.append(dict(case=mode,status='REJECTED',reason=str(e),from_actual_object=v['sha256']))
                    def reject(case,expected,action):
                        try:action()
                        except (ValueError,policy.AuditError) as e:
                            if expected not in str(e):raise
                            negatives.append(dict(case=case,status='REJECTED',reason=str(e)));return
                        raise ValueError('Negative accepted: '+case)
                    if not args.negative_sdk:raise ValueError('Explicit existing negative SDK27 required for native calibration')
                    sdk27=Path(args.negative_sdk)
                    if json.loads((sdk27/'SDKSettings.json').read_text())['Version']!='27.0':raise ValueError('Negative calibration SDK is not 27.0')
                    reject('SDK27_SELECTION','SDK_VERSION_MISMATCH',lambda:target.sdk_info(sdk27))
                    reject('SDK27_HEADER','UNAPPROVED_HEADER_OR_MIXED_SDK',lambda:target.dependency(sdk27/'usr/include/stdio.h',sdk,resource_dir))
                    reject('LEGACY_SOURCE_REFERENCE','REFERENCE_VERSION_MISMATCH',lambda:target.reference(json.loads(safe.checked('reports/m11/local/target-export-reference.json').read_text())))
                    changed=json.loads(json.dumps(ref));changed['files'][0]['text']+='\n'
                    reject('SOURCE_REFERENCE_HASH','REFERENCE_HASH_MISMATCH',lambda:target.reference(changed))
                    reject('WRONG_FILE_FORMAT','architecture_or_type',lambda:policy.inspect(b'NOT_A_MACHO_FILE'+bytes(32),'x86_64'))
                    for mode,changed_flags in [('LEGACY_DEPLOYMENT',[str(x).replace('-mmacosx-version-min=26.5','-mmacosx-version-min=15.0') for x in flags]),('SDK27_OBJECT',[str(sdk27) if x==sdk else str(x) for x in flags])]:
                        bad=badfolder/(mode+'.o');run(changed_flags+['-DN44_POLICY_UNKNOWN','-c',fixture,'-o',bad],'negative-compile-'+mode)
                        reject(mode,'OBJECT_TARGET_VERSION_MISMATCH',lambda p=bad:target.object_target(policy.inspect(p.read_bytes(),'x86_64')))
                    mismatch=run(flags+['-DN44_ABI_MISMATCH','-c',safe.ROOT/'tests/unit/m13_negative.cpp','-o',badfolder/'abi-mismatch.o'],'negative-ABI-type',allow=True)
                    if mismatch.returncode==0 or 'deliberately wrong API ABI' not in mismatch.stderr:raise ValueError('ABI mismatch not detected')
                    negatives.append(dict(case='ABI_TYPE_MISMATCH',status='REJECTED',compiler_exit=mismatch.returncode))
                    forbidden=badfolder/'illegal-init.o';run(flags+['-DN44_ILLEGAL_INIT','-c',safe.ROOT/'tests/unit/m13_negative.cpp','-o',forbidden],'negative-illegal-init')
                    rejected=policy.audit([dict(source='tests/unit/m13_negative.cpp',flags=[str(x) for x in flags],image=image(forbidden,arch))],{p.relative_to(safe.ROOT).as_posix() for p in NATIVE},allowed,exports_by_arch[arch])
                    if rejected['status']!='REJECTED':raise ValueError('Forbidden source path accepted')
                    negatives.append(dict(case='ILLEGAL_INITIALIZATION_PATH',status='REJECTED',errors=rejected['errors']))
                else:
                    try:policy.inspect(objects[0].read_bytes(),'x86_64');raise ValueError('Wrong architecture accepted')
                    except policy.AuditError as e:negatives.append(dict(case='WRONG_ARCHITECTURE',status='REJECTED',reason=str(e),actual='arm64',requested='x86_64'))
                    analysis=[]
                    for src in [P/'darwin_native.cpp',P/'darwin_snapshot.cpp',P/'darwin_gate.cpp',safe.ROOT/'tests/unit/m11_native_compile.cpp',safe.ROOT/'tests/unit/m12_native_compile.cpp']:
                        r=run(flags+['--analyze',src,'-o',folder/(src.stem+'.plist')],'native-analyze-'+src.stem)
                        if 'warning:' in r.stdout+r.stderr:raise ValueError('Native analyzer warning')
                        analysis.append(src.relative_to(safe.ROOT).as_posix())
                    summary['Native_Static_Analyzer']=dict(status='PASS',units=len(analysis))
            # Preserve complete tables locally; public evidence keeps counts and hashes.
            safe.write(local/'native-tables.json',json.dumps(public(native),indent=2))
            safe.write(local/'link-tables.json',json.dumps(public(links),indent=2))
            def compact(im):
                return {**{k:v for k,v in im.items() if k not in ('symbols','relocations')},
                    'symbol_count':len(im['symbols']),'relocation_count':len(im['relocations']),
                    'undefined':sorted(s['name'] for s in im['symbols'] if s['undefined'])}
            for item in native.values():
                for obj in item['objects']:obj['image']=compact(obj['image'])
            for item in links.values():
                item['partial_artifact']=compact(item['partial_artifact'])
                if 'image' in item:item['image']=compact(item['image'])
            save('native-object-results',native);save('symbol-audit',audits);save('link-results',links);save('abi-audit',dict(architectures=abi,current_SDK_layout=layouts,export_references=reference_files))
            save('negative-results',dict(status='PASS',cases=negatives));summary.update(Kernel_Object_Compile='PASS',Partial_Link='PASS',MH_KEXT_BUNDLE_Construction='PASS',KPI_Reference_Audit='PASS reference classification only',negative_cases=len(negatives))
        if args.target=='all':
            for src in [*previous.PURE,*MODELS]:
                r=run(base+['-arch','arm64',*cpu,'--analyze',src,'-o',build/(src.stem+'.plist')],'cpu-analyze-'+src.stem)
                if 'warning:' in r.stdout+r.stderr:raise ValueError('CPU analyzer warning')
            summary['CPU_Static_Analyzer']=dict(status='PASS',units=len(previous.PURE)+len(MODELS))
        # Every normal Clang command emits an actual .d file. Negative SDK27
        # objects and the explicitly labelled legacy baseline are excluded here.
        dependencies={}
        depfiles=[*build.rglob('*.d'),*safe.checked('build/m13/regression').rglob('*.d'),*local.glob('*-headers.d')]
        host_cpp=compiler.parent.parent/'include/c++/v1'
        for dep in depfiles:
            if dep.name.startswith('negative-') or dep.parent.name=='negative':continue
            entries={}
            for filename in shlex.split(dep.read_text().replace('\\\n',''))[1:]:
                p=Path(filename);category=target.dependency(p,sdk,resource_dir,host=True,host_cpp=host_cpp)
                entries[str(p)]=dict(category=category,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
            dependencies[dep.relative_to(safe.ROOT).as_posix()]=entries
        safe.write(local/'header-tables.json',json.dumps(public(dependencies),indent=2))
        unique={};compilations={}
        for dep,entries in dependencies.items():
            for path,record in entries.items():
                if path in unique and unique[path]!=record:raise ValueError('Header changed during compilation')
                unique[path]=record
            compilations[dep]=dict(headers=len(entries),dependency_set_sha256=hashlib.sha256(json.dumps(entries,sort_keys=True).encode()).hexdigest())
        save('header-dependencies',dict(status='PASS',unique_headers=unique,compilations=compilations,full_tables='ignored local/checks/header-tables.json',normal_SDK_mixing_findings=0))
        if any(hashlib.sha256(safe.checked(p).read_bytes()).hexdigest()!=v for p,v in hashes.items()):raise ValueError('Source changed during checks')
        summary.update(source_stability='PASS',status='COMPLETE_WITH_BLOCKERS',
            OBJECT_COMPILE=summary['Kernel_Object_Compile'],PARTIAL_LINK=summary['Partial_Link'],MACHO_KEXT_CONSTRUCTION=summary['MH_KEXT_BUNDLE_Construction'],
            SDK26_ABI_AUDIT='PASS declarations/object layout only' if summary['Kernel_Object_Compile']=='PASS' else 'NOT RUN',
            TARGET_BINARY_KPI_AUDIT='BLOCKED: matching target binary/KDK absent',TARGET_ABI_CLOSURE='BLOCKED',LOADABLE_KEXT='UNVERIFIED',KERNEL_RUNTIME='NOT RUN',GPU_RUNTIME='NOT RUN')
    except Exception as e:summary.update(status='FAIL',error=str(e));raise
    finally:save('test-results',summary)
    print(json.dumps(public(summary),indent=2))
if __name__=='__main__':main()
