"""M11 explicit CPU/object/offline-link checks; BSD-3-Clause.

Existing Apple tools only, serial children with timeouts. No downloads, bundles,
signing, installation, registry changes, native execution or hardware targets.
Full-link attempt uses strict undefined-symbol errors; no stubs/dynamic_lookup.
"""
import argparse,hashlib,importlib.util,json,os,platform,re,resource,shlex,struct,subprocess,sys,time
from pathlib import Path
if sys.version_info<(3,11):raise SystemExit("Existing Python 3.11+ required")
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m7_safety as safe
import run_host_tests as host
P=host.SRC.parent/"platform"
PURE=[*host.PURE,P/"lifecycle.cpp",P/"shutdown.cpp"]
NATIVE=[*PURE,P/"darwin_native.cpp",P/"darwin_snapshot.cpp",safe.ROOT/"tests/unit/m8_contract_compile.cpp",
        safe.ROOT/"tests/unit/m10_contract_compile.cpp",safe.ROOT/"tests/unit/m11_native_compile.cpp",safe.ROOT/"tests/unit/m11_kmod_compile.cpp"]
FORBIDDEN=("__cxa_","__gxx_personality","_Unwind","__dynamic_cast","_ZTI","_ZTS","_ZNSt","_Znwm","_Znam","_Zdl","_Zda","_malloc","_free","_puts","_printf","_fwrite","_pthread_","stack_chk")
def macho(path,arch,expected_kind=1):
    raw=safe.checked(path).read_bytes()
    if len(raw)<32:raise ValueError("Truncated header")
    magic,cpu,subtype,kind,n,size,flags,_=struct.unpack_from("<IiiIIIII",raw)
    if magic!=0xfeedfacf or cpu!={"arm64":0x100000c,"x86_64":0x1000007}[arch] or kind!=expected_kind:raise ValueError("Wrong Mach-O kind/architecture")
    if 32+size>len(raw):raise ValueError("Load command bounds")
    pos=32;versions=[];sections=[]
    for _ in range(n):
        cmd,length=struct.unpack_from("<II",raw,pos)
        if length<8 or pos+length>32+size:raise ValueError("Command bounds")
        if cmd in (0xc,0x80000018,0x8000001f,0x80000028,0x5):raise ValueError("Unexpected object entry/dylib")
        if cmd==0x32:versions.append(struct.unpack_from("<III",raw,pos+8))
        if cmd==0x19:
            count=struct.unpack_from("<I",raw,pos+64)[0]
            if 72+count*80>length:raise ValueError("Section range")
            for i in range(count):sections.append(raw[pos+72+i*80:pos+88+i*80].split(b"\0")[0].decode())
        pos+=length
    if pos!=32+size or (expected_kind==1 and not versions) or any(v[0]!=1 for v in versions):raise ValueError("macOS platform/layout")
    if any(s in sections for s in ("__mod_init_func","__gcc_except_tab","__init")):raise ValueError("Unexpected global initializer/EH")
    return dict(path=path.relative_to(safe.ROOT).as_posix(),arch=arch,cpu=cpu,subtype=subtype,type="MH_OBJECT" if kind==1 else "MH_KEXT_BUNDLE",build_version=versions,sections=sections,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler",required=True);parser.add_argument("--sdk",required=True)
    parser.add_argument("--target",required=True,choices=["host","objects","offline-link","all"])
    parser.add_argument("--export-reference",help="Existing reviewed pinned public XNU reference JSON; never fetched automatically")
    args=parser.parse_args()
    if sys.platform!="darwin" or platform.machine()!="arm64":raise SystemExit("Authorized arm64 macOS Host required")
    compiler,sdk=Path(args.compiler),Path(args.sdk)
    if not compiler.is_absolute() or not compiler.is_file() or not sdk.is_absolute() or not sdk.is_dir():raise SystemExit("Existing Apple tools/SDK required")
    out=safe.mkdir("reports/m11");local=safe.mkdir(out/"local/checks");build=safe.mkdir("build/m11/checks");tmp=safe.mkdir("tmp/m11/checks")
    env=os.environ.copy();env.update(TMPDIR=str(tmp),TMP=str(tmp),TEMP=str(tmp),CLANG_MODULE_CACHE_PATH=str(safe.mkdir(build/"cache")),PYTHONDONTWRITEBYTECODE="1",
        ASAN_OPTIONS="halt_on_error=1:detect_leaks=0:abort_on_error=0",UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1",TSAN_OPTIONS="halt_on_error=1")
    for k in ("CPATH","CPLUS_INCLUDE_PATH","C_INCLUDE_PATH","LIBRARY_PATH","DYLD_INSERT_LIBRARIES"):env.pop(k,None)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));records=[]
    def public(v):
        if isinstance(v,Path):return public(str(v))
        if isinstance(v,str):return v.replace(str(safe.ROOT),"PROJECT_ROOT").replace(str(sdk),"SDK_ROOT").replace(sys.executable,"PYTHON_EXECUTABLE")
        if isinstance(v,list):return [public(x) for x in v]
        if isinstance(v,dict):return {public(k):public(x) for k,x in v.items()}
        return v
    def save(name,data):safe.write(out/(name+".json"),json.dumps(public(data),ensure_ascii=False,indent=2))
    def run(cmd,name,data=None,timeout=60,allow=False):
        cmd=[str(x) for x in cmd]
        if "-o" in cmd:safe.checked(cmd[cmd.index("-o")+1])
        print(name,flush=True);begin=time.monotonic()
        try:r=subprocess.run(cmd,cwd=safe.ROOT,env=env,input=data,capture_output=True,text=True,timeout=timeout)
        except subprocess.TimeoutExpired as e:
            safe.write(local/(name+".log"),"TIMEOUT\n"+str(e.stdout)+str(e.stderr));records.append(dict(name=name,argv=cmd,exit=None,status="TIMEOUT"));save("commands",records);raise
        safe.write(local/(name+".log"),r.stdout+r.stderr);records.append(dict(name=name,argv=cmd,exit=r.returncode,seconds=round(time.monotonic()-begin,3)))
        safe.write(local/"commands-raw.json",json.dumps(records,indent=2));save("commands",records)
        if r.returncode and not allow:raise RuntimeError(name+" failed; raw log retained")
        return r
    before={p.relative_to(safe.ROOT).as_posix():hashlib.sha256(safe.checked(p).read_bytes()).hexdigest() for p in [*NATIVE,P/"contract.hpp",P/"lifecycle.hpp",P/"shutdown.hpp",P/"darwin_owner_storage.hpp",safe.ROOT/"tests/unit/m11_lifecycle.cpp",Path(__file__)]}
    save("executed-source-sha256",before)
    summary=dict(stage="M11",status="RUNNING",Core_Compile="NOT RUN",Native_Compile="NOT RUN",Partial_Link="NOT RUN",KPI_Audit="NOT RUN",Full_Link_Attempt="NOT RUN",Full_Kext_Link="NOT RUN",Bundle="NOT RUN",Sign="NOT RUN",Install="NOT RUN",Load="NOT RUN",Kernel_Runtime="NOT RUN",GPU_Runtime="NOT RUN",Windows_Regression="NOT RUN",x86_64_Host_Runtime="NOT RUN")
    try:
        version=run([compiler,"--version"],"compiler-version").stdout
        if "Apple clang" not in version:raise ValueError("Apple compiler required")
        tools={n:run(["xcrun","--find",n],"find-"+n).stdout.strip() for n in ("ld","nm","otool","lipo","dwarfdump")}
        linker=run([tools["ld"],"-v"],"ld-version");osver=run(["sw_vers"],"macos-version");xcode=run(["xcodebuild","-version"],"xcode-version")
        sdksettings=json.loads((sdk/"SDKSettings.json").read_text());sdkversion=sdksettings["Version"]
        save("environment",dict(compiler=version,linker=linker.stdout+linker.stderr,macOS=osver.stdout,Xcode=xcode.stdout,sdk=str(sdk),sdk_version=sdkversion,Python=sys.version,
            Intel_reference="macOS 15.0 / XNU 11215.1.10",header_match="UNVERIFIED: current SDK differs from target",deployment_label="15.0 is only a compile label",host_arch=platform.machine()))
        base=[compiler,"-std=c++17","-Wall","-Wextra","-Werror","-UNDEBUG","-O1","-g","-isysroot",sdk,"-mmacosx-version-min=15.0","-I"+str(host.SRC)]
        cpu=["-fno-exceptions","-fno-rtti","-ffreestanding","-Wframe-larger-than=4096"]
        if args.target in ("host","all"):
            original=safe.checked("run_host_tests.py").read_text()
            helper=original.replace("sys.path.insert(0, str(Path(__file__).resolve().parent))","sys.path.insert(0, "+repr(str(safe.ROOT))+")")
            for old,new in [('safe.mkdir("build/" + args.stage)','safe.mkdir("build/m11/checks/host/" + args.stage)'),('safe.mkdir("reports/" + args.stage)','safe.mkdir("reports/m11/local/checks/host/" + args.stage)'),('safe.mkdir("tmp/" + args.stage)','safe.mkdir("tmp/m11/checks/host/" + args.stage)')]:
                if helper.count(old)!=1:raise ValueError("Reviewed helper boundary changed")
                helper=helper.replace(old,new)
            helper_path=safe.write(build/"portable-helper.py",helper);regression={};tests={}
            for stage,arch,opts in [("m9-arm64","arm64",[]),("m9-x86_64","x86_64",["--compile-only","--skip-python"]),("m9-sanitized","arm64",["--sanitize","--skip-python"])]:
                run([sys.executable,"-I","-B","-X","utf8",helper_path,"--compiler",compiler,"--sdk",sdk,"--stage",stage,"--arch",arch,*opts],stage,timeout=600)
                result=json.loads(safe.checked(local/"host"/stage/"results.json").read_text());assert result["status"]=="PASS";regression[stage]=result
            for mode,flags in [("normal",[]),("asan-ubsan",["-fsanitize=address,undefined","-fno-omit-frame-pointer"]),("tsan",["-fsanitize=thread","-fno-omit-frame-pointer"])]:
                objects=[]
                for src in [P/"lifecycle.cpp",P/"shutdown.cpp"]:
                    obj=build/(mode+"-"+src.stem+".o");run(base+["-arch","arm64",*cpu,*flags,"-c",src,"-o",obj],mode+"-compile-"+src.stem);objects.append(obj)
                for test in ["m10_lifecycle","m11_lifecycle"]:
                    exe=build/(mode+"-"+test);parser_objs=[build/"host"/("m9-sanitized" if mode=="asan-ubsan" else "m9-arm64")/(p.stem+".o") for p in host.PURE]
                    run(base+["-arch","arm64",*flags,safe.ROOT/("tests/unit/"+test+".cpp"),*objects,*parser_objs,"-o",exe],mode+"-link-"+test)
                    log=run([exe],mode+"-run-"+test,timeout=30).stdout;m=re.search(r"SUMMARY (\d+) (\d+)",log)
                    if not m or int(m[2]) or "FAIL " in log:raise RuntimeError("Behavior failure")
                    tests[mode+"/"+test]=dict(PASS=int(m[1]),FAIL=int(m[2]))
            spec=importlib.util.spec_from_file_location("m11fixtures",safe.checked("tests/fixtures/m9_differential.py"));fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
            diffs={}
            for stage,flags in [("m9-arm64",[]),("m9-sanitized",["-fsanitize=address,undefined","-fno-omit-frame-pointer"])]:
                folder=build/"host"/stage;probe=folder/"probe"
                run(base+["-arch","arm64",*flags,safe.ROOT/"tests/unit/m65_probe.cpp",folder/"offlinevalidation.o",*[folder/(p.stem+".o") for p in host.PURE],"-o",probe],stage+"-probe-link")
                for name,inputs in [("shared",fixture.all_cases),("mutation",fixture.fuzz_cases())]:
                    rows=run([probe],stage+"-"+name,data="".join(fixture.request(*c) for c in inputs),timeout=30).stdout.splitlines()
                    if len(rows)!=len(inputs):raise RuntimeError("Row count")
                    errors=[i for i,(row,c) in enumerate(zip(rows,inputs)) if json.loads(row)!=fixture.canonical(*c)]
                    if errors:raise RuntimeError("Differential mismatch")
                    diffs[stage+"/"+name]=dict(inputs=len(inputs),differences=0)
            summary.update(Core_Compile="PASS",Host_Regression=regression,behavior=tests,differential=diffs,ASan_UBSan="PASS; leak detection NOT VERIFIED",TSan="PASS covered Host state/gate paths; kernel synchronization UNVERIFIED")
            save("build-results",dict(Host=regression,behavior=tests,differential=diffs))
        if args.target in ("objects","offline-link","all"):
            if not args.export_reference:raise ValueError("Explicit existing pinned reference required")
            reference=json.loads(safe.checked(args.export_reference).read_text())
            if reference["pin"]!="8d741a5de7ff4191bf97d57b9f54c2f6d4a15585":raise ValueError("Wrong Intel reference")
            exports={}
            for f in reference["files"]:
                if hashlib.sha256(f["text"].encode()).hexdigest()!=f["sha256"]:raise ValueError("Changed reference")
                for line in f["text"].splitlines():
                    line=line.strip()
                    if line.startswith("_"):exports[line.split()[0].split(":")[0]]=dict(file=f["path"],entry=line,file_sha256=f["sha256"])
            native={};symbols={};links={};abi={};kernel=sdk/"System/Library/Frameworks/Kernel.framework/Headers"
            for arch in ("x86_64","arm64"):
                folder=safe.mkdir(build/("darwin-"+arch));objects=[];items=[];defined={};undefined={};deps={}
                flags=base+["-arch",arch,*cpu,"-isystem",kernel,"-nostdinc++","-DKERNEL","-DKERNEL_EXTENSION","-mkernel","-fapple-kext","-fno-stack-protector"]
                if arch=="x86_64":flags+=["-mno-red-zone"]
                for src in NATIVE:
                    obj=folder/(src.stem+".o");dep=folder/(src.stem+".d");run(flags+["-MD","-MF",dep,"-c",src,"-o",obj],arch+"-compile-"+src.stem);objects.append(obj);item=macho(obj,arch)
                    u=run([tools["nm"],"-u",obj],arch+"-undefined-"+src.stem).stdout.splitlines();d=run([tools["nm"],"-gU",obj],arch+"-defined-"+src.stem).stdout.splitlines()
                    if any(t in s for s in u for t in FORBIDDEN):raise RuntimeError("Forbidden Host/EH/RTTI import")
                    for s in u:undefined.setdefault(s,[]).append(src.relative_to(safe.ROOT).as_posix())
                    for line in d:
                        parts=line.split()
                        if len(parts)>=3:defined.setdefault(parts[-1],[]).append(src.relative_to(safe.ROOT).as_posix())
                    item["undefined"]=u;items.append(item)
                    for path in shlex.split(dep.read_text().replace("\\\n",""))[1:]:
                        p=Path(path)
                        if p.is_relative_to(sdk):deps[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
                combined=folder/"n44-offline-partial.o"
                run([tools["ld"],"-r","-arch",arch,"-platform_version","macos","15.0",sdkversion,"-o",combined,*objects],arch+"-partial-link")
                part=macho(combined,arch);remaining=run([tools["nm"],"-u",combined],arch+"-partial-undefined").stdout.splitlines()
                if any(x in defined for x in remaining):raise RuntimeError("Internal symbols unresolved")
                for name,opts in [("file",None),("lipo",["-archs"]),("otool",["-h","-l","-r"]),("dwarfdump",["--verify"])]:
                    run(["file" if name=="file" else tools[name],*(opts or []),combined],arch+"-partial-"+name)
                audit=[dict(symbol=s,classification="INTERNAL_RESOLVED" if s in defined else "VERIFIED_EXPORT_REFERENCE" if s in exports and arch=="x86_64" else "UNRESOLVED_ABI_REQUIREMENT",users=users,providers=defined.get(s,[]),export_reference=exports.get(s) if arch=="x86_64" else None,target_binary_verified=False) for s,users in sorted(undefined.items())]
                symbols[arch]=dict(per_symbol=audit,remaining=remaining,unknown=[s for s in remaining if arch=="x86_64" and s not in exports],reference_scope="macOS 15.0 XNU source x86_64 export lists; not a target kernel binary")
                native[arch]=dict(status="PASS",objects=items,flags=flags,header_sha256=deps);links[arch]=dict(Partial_Link="PASS",artifact=part,partial_artifact=part,remaining=remaining)
                abi[arch]=dict(object_options_layout="PASS",target_sdk_match="BLOCKED: macOS 15 SDK absent",target_kernel_binary_exports="UNVERIFIED",Cxx_class_vtable_runtime="NOT RUN",generic_arm64_not_arm64e=True)
                if arch=="x86_64" and args.target in ("offline-link","all"):
                    if symbols[arch]["unknown"]:raise RuntimeError("Unknown import blocks offline link attempt")
                    linked=folder/"n44-offline-linked.macho"
                    r=run([tools["ld"],"-kext","-arch",arch,"-platform_version","macos","15.0",sdkversion,"-undefined","error","-o",linked,combined],"strict-kext-link-attempt",allow=True)
                    links[arch].update(Full_Link_Attempt="EXECUTED",exit=r.returncode,Link_Result="FAIL" if r.returncode else "UNVERIFIED OUTPUT: must inspect before declaring a kext",explicit_undefined_tolerance=False,linker_retains_kernel_imports=True,Bundle="NOT RUN",Sign="NOT RUN",Install="NOT RUN",Load="NOT RUN")
                    if r.returncode==0:
                        image=macho(linked,arch,11)
                        run([tools["otool"],"-h","-l","-r",linked],"full-link-header")
                        imported=run([tools["nm"],"-u",linked],"full-link-imports").stdout.splitlines()
                        if imported!=remaining:raise RuntimeError("Final image import set changed")
                        run(["file",linked],"full-link-file");run([tools["lipo"],"-archs",linked],"full-link-lipo")
                        run([tools["otool"],"-tvV",folder/"m11_native_compile.o"],"service-vtable-disassembly")
                        links[arch].update(Link_Result="PASS: static MH_KEXT_BUNDLE construction only",artifact=image,Target_ABI="BLOCKED: target SDK/kernel binary absent",KPI_Resolution="UNVERIFIED: imports retained")
                        # Actual Host import calibrates linker limitations. This
                        # negative output is isolated and never a valid kernel target.
                        negative=folder/"policy-host-puts.o";badimage=folder/"policy-invalid-image.macho"
                        run(base+["-arch",arch,"-c",safe.ROOT/"tests/unit/m10_host_dependency.cpp","-o",negative],"negative-host-import-compile")
                        leaks=run([tools["nm"],"-u",negative],"negative-host-import-symbols").stdout.splitlines()
                        if "_puts" not in leaks or "_puts" in exports:raise RuntimeError("Negative policy calibration changed")
                        rejected=any(t in s for s in leaks for t in FORBIDDEN)
                        if not rejected:raise RuntimeError("Independent symbol policy failed")
                        nr=run([tools["ld"],"-kext","-arch",arch,"-undefined","error","-o",badimage,combined,negative],"negative-linker-calibration",allow=True)
                        links[arch]["negative_policy"]=dict(actual_host_import="_puts",independent_audit="REJECTED",linker_exit=nr.returncode,
                            meaning="Kext linker construction can retain unsupported imports; linker exit is not KPI validation",negative_image_never_executed=True)
                    summary.update(Full_Link_Attempt="EXECUTED",Offline_Image="FAIL" if r.returncode else "PASS: static MH_KEXT_BUNDLE; no Bundle/runtime",Full_Kext_Link="FAIL" if r.returncode else "UNVERIFIED: target ABI/KPI resolution blocked")
                if arch=="arm64":
                    for src in [P/"darwin_native.cpp",P/"darwin_snapshot.cpp",safe.ROOT/"tests/unit/m11_native_compile.cpp"]:
                        r=run(flags+["--analyze",src,"-o",folder/(src.stem+".plist")],"native-analyze-"+src.stem)
                        if "warning:" in r.stdout+r.stderr:raise RuntimeError("Native analyzer warning")
                    save("native-analysis",dict(status="PASS",units=3,warnings=0,API_runtime="NOT RUN"))
            save("native-object-results",native);save("symbol-audit",symbols);save("abi-audit",abi);save("link-results",links)
            summary.update(Native_Compile="PASS",Partial_Link="PASS",KPI_Audit="PASS reference classification; target ABI UNVERIFIED")
        if args.target=="all":
            analysis=[]
            for src in PURE:
                r=run(base+["-arch","arm64",*cpu,"--analyze",src,"-o",build/(src.stem+".plist")],"analyze-"+src.stem)
                if "warning:" in r.stdout+r.stderr:raise RuntimeError("Static analyzer warning")
                analysis.append(src.relative_to(safe.ROOT).as_posix())
            summary["Static_Analyzer"]=dict(status="PASS",units=len(analysis),files=analysis)
        if any(hashlib.sha256(safe.checked(p).read_bytes()).hexdigest()!=v for p,v in before.items()):raise ValueError("Source changed during checks")
        summary["source_stability"]="PASS";summary["status"]="COMPLETE_WITH_BLOCKERS" if summary["Full_Kext_Link"]!="NOT RUN" else "PASS"
    except Exception as e:summary.update(status="FAIL",error=str(e));raise
    finally:save("test-results",summary)
    print(json.dumps(public(summary),indent=2))
if __name__=="__main__":main()
