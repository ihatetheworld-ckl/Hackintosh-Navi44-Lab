"""M10 reviewed serial CPU/object checks; BSD-3-Clause.

Existing Apple tools only. No download, installation, Makefile, deployable
bundle, kernel entry, codesign, GPU or native execution. Partial outputs must
be MH_OBJECT without dynamic-library loads or entry-point load commands.
Raw execution logs remain local; public JSON replaces private argv prefixes.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import platform
import re
import resource
import struct
import subprocess
import sys
import time

if sys.version_info<(3,11):raise SystemExit("Existing Python 3.11+ required")
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m7_safety as safe
import run_host_tests as host
PLATFORM=host.SRC.parent/"platform"
LIFETIME=PLATFORM/"lifecycle.cpp"
NATIVE=[PLATFORM/"darwin_native.cpp",PLATFORM/"darwin_snapshot.cpp"]
PROBE=safe.checked("tests/unit/m10_contract_compile.cpp")
M9="498e97fd3e92fbb243e303fcc381a4a6e6bef07b"

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler",required=True);parser.add_argument("--sdk",required=True)
    parser.add_argument("--target",required=True,choices=["host","native","partial-link","all"])
    args=parser.parse_args()
    if sys.platform!="darwin" or platform.machine()!="arm64":raise SystemExit("Authorized arm64 Mac required")
    compiler,sdk=Path(args.compiler),Path(args.sdk)
    if not compiler.is_absolute() or not compiler.is_file() or not sdk.is_absolute() or not sdk.is_dir():raise SystemExit("Existing tools/SDK required")
    out=safe.mkdir("reports/m10");local=safe.mkdir(out/"local");build=safe.mkdir("build/m10");tmp=safe.mkdir("tmp/m10")
    env=os.environ.copy();env.update(TMPDIR=str(tmp),TMP=str(tmp),TEMP=str(tmp),
        CLANG_MODULE_CACHE_PATH=str(safe.mkdir(build/"cache")),PYTHONDONTWRITEBYTECODE="1",
        ASAN_OPTIONS="halt_on_error=1:detect_leaks=0:abort_on_error=0",UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1",
        TSAN_OPTIONS="halt_on_error=1")
    for key in ("CPATH","CPLUS_INCLUDE_PATH","C_INCLUDE_PATH","LIBRARY_PATH","DYLD_INSERT_LIBRARIES"):env.pop(key,None)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    records=[]
    def public(value):
        if isinstance(value,str):return value.replace(str(safe.ROOT),"<PROJECT_ROOT>").replace(sys.executable,"<EXISTING_PYTHON>")
        if isinstance(value,list):return [public(x) for x in value]
        if isinstance(value,dict):return {k:public(v) for k,v in value.items()}
        return value
    def save(name,data):safe.write(out/(name+".json"),json.dumps(public(data),ensure_ascii=False,indent=2))
    def run(command,name,data=None,timeout=60,allow_failure=False):
        command=[str(x) for x in command]
        if "-o" in command:safe.checked(command[command.index("-o")+1])
        print(name,flush=True);start=time.monotonic()
        try:p=subprocess.run(command,cwd=safe.ROOT,env=env,input=data,capture_output=True,text=True,timeout=timeout)
        except subprocess.TimeoutExpired as e:
            records.append(dict(name=name,argv=command,exit=None,status="TIMEOUT"));save("commands",records)
            safe.write(local/(name+".log"),"TIMEOUT\n"+str(e.stdout)+str(e.stderr));raise
        safe.write(local/(name+".log"),p.stdout+p.stderr)
        records.append(dict(name=name,argv=command,exit=p.returncode,seconds=round(time.monotonic()-start,3)))
        safe.write(local/"commands-raw.json",json.dumps(records,indent=2));save("commands",records)
        if p.returncode and not allow_failure:raise RuntimeError(name+" failed; original local log retained")
        return p
    summary=dict(stage="M10",status="RUNNING",Core_Compile="NOT RUN",Native_Compile="NOT RUN",
        Partial_Link="NOT RUN",Symbol_Audit="NOT RUN",ABI_Audit="NOT RUN",Full_Kext_Link="NOT RUN",
        Kernel_Runtime="NOT RUN",GPU_Runtime="NOT RUN",Windows_Regression="NOT RUN",x86_64_Host_Runtime="NOT RUN")
    save("test-results",summary)
    try:
        version=run([compiler,"--version"],"compiler-version").stdout
        if "Apple clang" not in version:raise RuntimeError("Apple compiler required")
        tools={name:run(["xcrun","--find",name],"find-"+name).stdout.strip() for name in ("ld","nm","otool","lipo","dwarfdump")}
        linker_version=run([tools["ld"],"-v"],"linker-version")
        save("environment",dict(compiler=version.strip(),sdk=str(sdk),python=sys.version,
            host_arch=platform.machine(),linker=(linker_version.stdout+linker_version.stderr).strip(),target=args.target))
        tracked=[x.decode() for x in subprocess.check_output(["git","ls-files","-z"]).split(b"\0") if x]
        paths=set(p for p in tracked if p.endswith((".cpp",".hpp",".h",".py")) and not p.startswith("reports/"))
        paths.update(p.relative_to(safe.ROOT).as_posix() for p in [LIFETIME,*NATIVE,PROBE,PLATFORM/"lifecycle.hpp",PLATFORM/"darwin_snapshot.hpp",
            safe.checked("tests/unit/m10_lifecycle.cpp"),safe.checked("development/AMDRadeonRDNA4-Navi44/host/lifecycle_mock.hpp"),safe.checked(__file__)])
        before={p:hashlib.sha256(safe.checked(p).read_bytes()).hexdigest() for p in sorted(paths)};save("source-sha256",before)
        common=[compiler,"-std=c++17","-Wall","-Wextra","-Werror","-UNDEBUG","-O1","-g","-isysroot",sdk,
                "-mmacosx-version-min=13.0","-I"+str(host.SRC)]
        cpu=["-fno-exceptions","-fno-rtti","-ffreestanding","-Wframe-larger-than=4096"]
        if args.target in ("host","all"):
            summary["Regression_Calibration"]="NOT RUN: original private M9 history intentionally absent; M10 current behavior tested below"
            original=safe.checked("run_host_tests.py").read_text()
            helper=original.replace("str(Path(__file__).resolve().parent)",repr(str(safe.ROOT)))
            for old,new in [('safe.mkdir("build/" + args.stage)','safe.mkdir("build/m10/host/" + args.stage)'),
                ('safe.mkdir("reports/" + args.stage)','safe.mkdir("reports/m10/local/host/" + args.stage)'),
                ('safe.mkdir("tmp/" + args.stage)','safe.mkdir("tmp/m10/host/" + args.stage)')]:
                if helper.count(old)!=1:raise RuntimeError("Historical helper boundary changed")
                helper=helper.replace(old,new)
            helper_path=safe.write(build/"host-helper.py",helper)
            host_results={}
            for stage,arch,opts in [("m9-arm64","arm64",[]),("m9-x86_64","x86_64",["--compile-only","--skip-python"]),("m9-sanitized","arm64",["--sanitize","--skip-python"])]:
                run([sys.executable,"-I","-B","-X","utf8",helper_path,"--compiler",compiler,"--sdk",sdk,"--stage",stage,"--arch",arch,*opts],stage,timeout=600)
                result=json.loads(safe.checked(local/"host"/stage/"results.json").read_text())
                if result["status"]!="PASS":raise RuntimeError("Regression failed")
                host_results[stage]=result
            spec=importlib.util.spec_from_file_location("m10fixtures",safe.checked("tests/fixtures/m9_differential.py"));fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
            cases=fixture.all_cases;mutations=fixture.fuzz_cases()
            if len(cases)!=744 or len(mutations)!=2400:raise RuntimeError("Finite corpus changed")
            lifetime_results={}
            for stage,sanitized in [("m9-arm64",False),("m9-sanitized",True)]:
                folder=safe.checked(build/"host"/stage);flags=["-fsanitize=address,undefined","-fno-omit-frame-pointer"] if sanitized else []
                base=common+["-arch","arm64",*flags]
                life=folder/"lifecycle.o";run(base+cpu+["-c",LIFETIME,"-o",life],stage+"-compile-lifecycle")
                objects=[folder/(p.stem+".o") for p in host.PURE]
                exe=folder/"m10_lifecycle"
                run(base+[safe.checked("tests/unit/m10_lifecycle.cpp"),life,*objects,"-o",exe],stage+"-link-lifecycle")
                log=run([exe],stage+"-run-lifecycle",timeout=30).stdout
                match=re.search(r"SUMMARY (\d+) (\d+)",log)
                if not match or int(match[2]) or "FAIL " in log:raise RuntimeError("Lifetime assertion failure")
                lifetime_results[stage]=dict(PASS=int(match[1]),FAIL=int(match[2]),failure_injection_inputs=600,concurrent_attempts=240)
                probe=folder/"probe"
                run(base+[safe.checked("tests/unit/m65_probe.cpp"),folder/"offlinevalidation.o",*objects,"-o",probe],stage+"-link-probe")
                for inputs,name in [(cases,"differential"),(mutations,"mutation")]:
                    output=run([probe],stage+"-"+name,data="".join(fixture.request(*c) for c in inputs),timeout=30).stdout.splitlines()
                    if len(output)!=len(inputs):raise RuntimeError("Differential row count mismatch")
                    differences=[dict(index=i,expected=fixture.canonical(*c),actual=json.loads(row)) for i,(c,row) in enumerate(zip(inputs,output)) if fixture.canonical(*c)!=json.loads(row)]
                    save(stage+"-"+name+"-differences",differences)
                    if differences:raise RuntimeError("Differential mismatch")
            # Compiler instrumentation includes the lifetime state machine and
            # Host synchronization mock. Pure immutable parsers are not concurrent.
            tsan_flags=common+["-arch","arm64","-fsanitize=thread","-fno-omit-frame-pointer"]
            tsan_obj=build/"lifecycle-tsan.o";tsan_exe=build/"lifetime-tsan"
            p=run(tsan_flags+cpu+["-c",LIFETIME,"-o",tsan_obj],"tsan-compile",allow_failure=True)
            tsan=dict(status="NOT RUN",scope="Ownership state + Host mock; existing non-concurrent parser objects not instrumented")
            if p.returncode==0:
                objects=[build/"host/m9-arm64"/(p.stem+".o") for p in host.PURE]
                p=run(tsan_flags+[safe.checked("tests/unit/m10_lifecycle.cpp"),tsan_obj,*objects,"-o",tsan_exe],"tsan-link",allow_failure=True)
                if p.returncode==0:
                    p=run([tsan_exe],"tsan-runtime",timeout=30,allow_failure=True)
                    text=p.stdout+p.stderr
                    if "WARNING: ThreadSanitizer: data race" in text:raise RuntimeError("ThreadSanitizer detected a real race")
                    if p.returncode==0 and re.search(r"SUMMARY \d+ 0",text):tsan["status"]="PASS"
                    elif "FATAL: ThreadSanitizer" in text or "Operation not permitted" in text:tsan["status"]="SKIP: runtime unsupported by current sandbox/environment"
                    else:raise RuntimeError("TSan test failed without an environmental blocker")
                else:tsan["status"]="SKIP: existing toolchain cannot link TSan"
            else:tsan["status"]="SKIP: existing compiler cannot build TSan"
            summary.update(Core_Compile="PASS",Host_Regression=host_results,Lifetime=lifetime_results,
                shared_differential=dict(inputs=744,differences=0),parser_mutation=dict(inputs=2400,seed=759070,differences=0),
                ASan_UBSan="PASS for current arm64 regression + lifecycle; leak detection NOT VERIFIED",TSan=tsan)
            save("build-results",dict(Host=host_results,Lifetime=lifetime_results,TSan=tsan))

        def macho(path,arch):
            raw=safe.checked(path).read_bytes();magic,cpu_type,subtype,kind,count,size,flags,_=struct.unpack_from("<IiiIIIII",raw)
            if magic!=0xfeedfacf or cpu_type!={"arm64":0x100000c,"x86_64":0x1000007}[arch] or kind!=1:raise RuntimeError("Wrong architecture or non-object artifact")
            offset=32;platforms=[];sections=[]
            if offset+size>len(raw):raise RuntimeError("Command range")
            for _ in range(count):
                cmd,length=struct.unpack_from("<II",raw,offset)
                if length<8 or offset+length>32+size:raise RuntimeError("Command bounds")
                if cmd in (0xc,0x80000018,0x8000001f,0x80000028,0x5):raise RuntimeError("Unexpected runtime entry/dylib command")
                if cmd==0x32:platforms.append(struct.unpack_from("<III",raw,offset+8))
                if cmd==0x19:
                    n=struct.unpack_from("<I",raw,offset+64)[0]
                    for i in range(n):sections.append(raw[offset+72+i*80:offset+88+i*80].split(b"\0")[0].decode())
                offset+=length
            if not platforms or any(p[0]!=1 for p in platforms):raise RuntimeError("Wrong platform")
            if any(s in sections for s in ("__mod_init_func","__gcc_except_tab","__init")):raise RuntimeError("Unexpected global initialization/EH section")
            return dict(path=path.relative_to(safe.ROOT).as_posix(),cpu=cpu_type,subtype=subtype,type="MH_OBJECT",build_version=platforms,sections=sections,sha256=hashlib.sha256(raw).hexdigest())
        native_results={};symbol_results={};partial_results={};kernel=sdk/"System/Library/Frameworks/Kernel.framework/Headers"
        if args.target in ("native","partial-link","all"):
            exported=json.loads(safe.checked(local/"export-reference.json").read_text())
            export_files={}
            for f in exported["files"]:
                if hashlib.sha256(f["text"].encode()).hexdigest()!=f["sha256"]:raise RuntimeError("Export source changed")
                for line in f["text"].splitlines():
                    line=line.strip()
                    if line.startswith("_"):
                        left=line.split()[0].split(":")[0];export_files.setdefault(f["path"],{})[left]=dict(file=f["path"],line=line)
            public_exports=[]
            forbidden=("__cxa_","__gxx_personality","_Unwind","__dynamic_cast","_ZTI","_ZTS","_ZNSt","_Znwm","_Znam","_Zdl","_Zda","_malloc","_free","_puts","_printf","_fwrite","_pthread_","stack_chk")
            negative=build/"host-import-negative.o"
            run(common+["-arch","arm64","-c",safe.checked("tests/unit/m10_host_dependency.cpp"),"-o",negative],"policy-negative-compile")
            leaked=run([tools["nm"],"-u",negative],"policy-negative-symbols").stdout.splitlines()
            if "_puts" not in leaked or not any(t in s for s in leaked for t in forbidden):raise RuntimeError("Host import policy failed to reject genuine puts import")
            summary["Symbol_Policy_Negative"]="PASS: actual Host SDK puts object rejected; never included in kernel link"
            for arch in ("x86_64","arm64"):
                exports={}
                for path,values in export_files.items():
                    if path.endswith((".x86_64.exports",".arm64.exports")) and not path.endswith("."+arch+".exports"):continue
                    exports.update(values)
                folder=safe.mkdir(build/("native-"+arch));objects=[];object_audit=[];defined={};undefined={}
                flags=common+["-arch",arch,"-isystem",kernel,"-nostdinc++","-DKERNEL","-DKERNEL_EXTENSION","-mkernel","-fapple-kext","-fno-stack-protector",*cpu]
                if arch=="x86_64":flags+=["-mno-red-zone"]
                sources=[*host.PURE,LIFETIME,*NATIVE,PROBE,safe.checked("tests/unit/m8_contract_compile.cpp")]
                for src in sources:
                    obj=folder/(src.stem+".o");objects.append(obj)
                    run(flags+["-MD","-MF",folder/(src.stem+".d"),"-c",src,"-o",obj],arch+"-compile-"+src.stem)
                    item=macho(obj,arch)
                    u=run([tools["nm"],"-u",obj],arch+"-undefined-"+src.stem).stdout.splitlines()
                    d=run([tools["nm"],"-gU",obj],arch+"-defined-"+src.stem).stdout.splitlines()
                    item["undefined_symbols"]=u;object_audit.append(item)
                    for symbol in u:undefined.setdefault(symbol,[]).append(src.relative_to(safe.ROOT).as_posix())
                    for line in d:
                        parts=line.split()
                        if len(parts)>=3:defined.setdefault(parts[-1],[]).append(src.relative_to(safe.ROOT).as_posix())
                    if any(t in s for s in u for t in forbidden):raise RuntimeError("Host/exception/RTTI/stack runtime in kernel object")
                # An actual correctly formed object must be rejected for the other CPU.
                try:macho(objects[0],"arm64" if arch=="x86_64" else "x86_64")
                except RuntimeError:pass
                else:raise RuntimeError("Architecture audit accepted the wrong CPU")
                audit=[]
                for symbol,users in sorted(undefined.items()):
                    if symbol in defined:classification="INTERNAL_RESOLVED"
                    elif symbol in exports:classification="EXPECTED_KERNEL_IMPORT"
                    elif any(t in symbol for t in forbidden):classification="HOST_ONLY_DEPENDENCY"
                    else:classification="UNKNOWN"
                    row=dict(symbol=symbol,classification=classification,users=users,providers=defined.get(symbol,[]),requires_real_kernel_link=symbol not in defined)
                    if symbol in exports:
                        row["export_reference"]=exports[symbol];public_exports.append(dict(symbol=symbol,**exports[symbol]))
                    audit.append(row)
                native_results[arch]=dict(status="PASS",objects=object_audit,flags=[str(x) for x in flags])
                symbol_results[arch]=dict(per_symbol=audit,unknown=[r["symbol"] for r in audit if r["classification"]=="UNKNOWN"])
                run([tools["dwarfdump"],"--verify",folder/(PROBE.stem+".o")],arch+"-verify-dwarf")
                if args.target in ("partial-link","all"):
                    combined=folder/"n44-offline-partial.o"
                    p=run([tools["ld"],"-r","-arch",arch,"-platform_version","macos","13.0","27.0","-o",combined,*objects],arch+"-partial-link",allow_failure=True)
                    if p.returncode:
                        partial_results[arch]=dict(status="FAIL",reason="Apple linker error; no unsafe fallback");continue
                    item=macho(combined,arch);remaining=run([tools["nm"],"-u",combined],arch+"-partial-undefined").stdout.splitlines()
                    if any(s in defined for s in remaining):raise RuntimeError("Unresolved internal symbol after partial link")
                    run([tools["otool"],"-r",combined],arch+"-partial-relocations")
                    run([tools["otool"],"-h","-l",combined],arch+"-partial-load-commands")
                    run(["file",combined],arch+"-partial-file");run([tools["lipo"],"-archs",combined],arch+"-partial-lipo")
                    item.update(status="PASS",remaining_imports=[dict(symbol=s,classification="EXPECTED_KERNEL_IMPORT" if s in exports else "UNKNOWN",requires_real_kernel_link=True) for s in remaining],deployable=False,Full_Kext_Link="NOT RUN")
                    partial_results[arch]=item
            save("native-object-results",native_results);save("symbol-audit",symbol_results);save("partial-link-results",partial_results)
            references={(r["symbol"],r["file"],r["line"]) for r in public_exports}
            save("export-reference",dict(pin=exported["pin"],origin=exported["origin"],scope=exported["scope"],file_sha256={f["path"]:f["sha256"] for f in exported["files"]},used_symbols=[dict(symbol=s,file=f,line=line) for s,f,line in sorted(references)]))
            summary.update(Core_Compile="PASS",Native_Compile="PASS",Symbol_Audit="PASS: classified; real kernel link remains required",
                ABI_Audit="PASS: arch/options/layout/DWARF/object invariants; kernel ABI runtime UNVERIFIED",
                Partial_Link="PASS" if partial_results and all(x["status"]=="PASS" for x in partial_results.values()) else "NOT RUN" if not partial_results else "FAIL")
        analysis=[]
        if args.target=="all":
            for src in [*host.PURE,LIFETIME,safe.checked("tests/unit/m8_contract_compile.cpp")]:
                p=run(common+["-arch","arm64","--analyze",*cpu,src,"-o",build/(src.stem+".plist")],"analyze-"+src.stem)
                if "warning:" in p.stdout+p.stderr:raise RuntimeError("Static analyzer warning")
                analysis.append(src.relative_to(safe.ROOT).as_posix())
            summary["Static_Analysis"]=dict(status="PASS",files=analysis)
        if any(hashlib.sha256(safe.checked(p).read_bytes()).hexdigest()!=v for p,v in before.items()):raise RuntimeError("Source changed during checks")
        summary["source_stability"]="PASS";summary["status"]="PASS" if summary["Partial_Link"]!="FAIL" else "PARTIAL"
    except Exception as exc:
        summary.update(status="FAIL",error=str(exc));raise
    finally:save("test-results",summary)
    print(json.dumps(public(summary),ensure_ascii=False,indent=2))

if __name__=="__main__":main()
