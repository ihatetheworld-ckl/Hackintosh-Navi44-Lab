"""Offline source/header comparison; no target_binary layout inference or downloads.

BSD-3-Clause. Run after run_m12_checks. Read-only Apple SDK, pinned reference
JSONs, recorded genuine objects. The lexical comparison includes conditional
source branches and is explicitly not a target ABI calculation.
"""
import argparse,hashlib,json,os,re,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m7_safety as safe
import m13_target as target
PIN=target.PROFILE['xnu_pin']
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--sdk',required=True);ap.add_argument('--reference',required=True);a=ap.parse_args()
    sdk=Path(a.sdk);kernel=sdk/'System/Library/Frameworks/Kernel.framework/Headers'
    tmp=safe.mkdir('tmp/m12/research');env=os.environ.copy();env.update(TMPDIR=str(tmp),TMP=str(tmp),TEMP=str(tmp))
    sdkversion=json.loads((sdk/'SDKSettings.json').read_text())['Version']
    native=json.loads(safe.checked('reports/m13/native-object-results.json').read_text())
    refs=[]
    for p in [a.reference]:
        data=json.loads(safe.checked(p).read_text())
        if data['pin']!=PIN:raise ValueError('Wrong pin')
        target.reference(data);refs+=data['files']
    def clean(t):return re.sub(r'//[^\n]*','',re.sub(r'/\*.*?\*/','',t,flags=re.S))
    def virtuals(t):
        return [' '.join(x.split()) for x in re.findall(r'\bvirtual\s+([^;{}]+?)(?:;|\{|=\s*0)',clean(t),re.S)]
    comparisons=[]
    for f in refs:
        if f['path'].startswith('config/'):continue
        text=f['text'];sha=hashlib.sha256(text.encode()).hexdigest()
        if f.get('sha256',sha)!=sha:raise ValueError('Changed source reference')
        rel=f['path'].replace('iokit/','',1).replace('libkern/libkern/','libkern/',1)
        installed=kernel/rel
        if not installed.is_file():raise ValueError('Current SDK header absent')
        current=installed.read_text();old=virtuals(text);new=virtuals(current)
        compiled_hash=hashlib.sha256(installed.read_bytes()).hexdigest()
        key='SDK_ROOT/'+installed.relative_to(sdk).as_posix()
        if any(item['header_sha256'].get(key,{}).get('sha256')!=compiled_hash for item in native.values()):raise ValueError('Reference SDK differs from actually compiled headers')
        comparisons.append(dict(path=f['path'],target_source_sha256=sha,current_SDK_header=rel,current_header_sha256=hashlib.sha256(installed.read_bytes()).hexdigest(),
            bytes_identical=text==current,lexical_virtuals_target=len(old),lexical_virtuals_current=len(new),
            declarations_only_in_target=[s for s in old if s not in new],declarations_only_in_current=[s for s in new if s not in old],
            declaration_order_equal=old==new,conditional_source_not_preprocessed=True,target_layout_verified=False))
    audit_path=safe.checked('reports/m13/abi-audit.json');abi=json.loads(audit_path.read_text())
    for arch,item in abi['current_SDK_layout'].items():
        raw=safe.checked('reports/m13/local/checks/'+arch+'-layout-compile.log').read_text()
        table=raw.split("Vtable for 'N44LayoutReference'",1)[1].split('\n\n',1)[0]
        slots=[]
        for index,decl in re.findall(r'^\s*(\d+) \| (.+)$',table,re.M):
            if re.search(r'(IOService|N44LayoutReference)::(init\(|start\(|stop\(|free\(|open\(|close\(|willTerminate\(|didTerminate\(|terminate\()',decl):
                slots.append(dict(table_index=int(index),offset_from_ZTV_symbol=int(index)*8,declaration=decl))
        if len(slots)!=10:raise ValueError('Current SDK layout probe changed')
        item['current_SDK_selected_vtable_entries']=slots
        item['target_binary_entries']='UNVERIFIED; never inferred from source lexical counts'
    abi.update(source_comparison=comparisons,source_scope='Conditional source is not SDK projection or a target binary',target_source_pin=PIN)
    safe.write(audit_path,json.dumps(abi,indent=2))
    symbols=json.loads(safe.checked('reports/m13/symbol-audit.json').read_text())
    links=json.loads(safe.checked('reports/m13/link-results.json').read_text());rows=[]
    # ABI descriptions match genuinely compiled current-SDK static_asserts.
    specs={
        '_IOMallocAligned':('IOKit/IOLib.h','void*(vm_size_t, vm_offset_t)','two 64-bit unsigned inputs; 64-bit pointer result','allocator; pair same size with IOFreeAligned'),
        '_IOFreeAligned':('IOKit/IOLib.h','void(void*, vm_size_t)','pointer64 + size64','release only after all users drain'),
        '_IOLog':('IOKit/IOLib.h','void(const char*, ...)','pointer64 + C varargs','no logging reentry while lifecycle gate held'),
        '_memcpy':('string.h','void*(void*, const void*, size_t)','three 64-bit values; pointer result','compiler lowering; checked CPU ranges'),
        '___bzero':('string.h (compiler builtin lowering)','x86 compiler-emitted __bzero','pointer64 + size64; void','exact compiler import is in source export list; target binary still needed'),
        '__ZN6OSData9withBytesEPKvj':('libkern/c++/OSData.h','OSPtr<OSData>(const void*, unsigned int)','pointer64 + uint32; raw pointer64 in audited SDK mode','factory count1, owner retains, drop factory, release after drain'),
        '__ZN24IOBufferMemoryDescriptor9withBytesEPKvmjb':('IOKit/IOBufferMemoryDescriptor.h','OSPtr<IOBufferMemoryDescriptor>(const void*, vm_size_t, IODirection, bool)','pointer64 + size64 + direction32 + bool; raw pointer64','CPU copy kIODirectionNone; never prepare/map/DMA'),
        '__ZTV9IOService':('IOKit/IOService.h','C++ vtable data symbol','inherited Apple kernel C++ table; qualified superclass calls use SDK-defined slots','symbol spelling alone cannot validate vtable; class unregistered/uninstantiable'),
        '_IORecursiveLockLock':('IOKit/IOLocks.h','void(IORecursiveLock*)','pointer64','borrowed lock lifetime must include waiters; sleepable context'),
        '_IORecursiveLockUnlock':('IOKit/IOLocks.h','void(IORecursiveLock*)','pointer64','balanced current-thread unlock; ordinary context remains required'),
        '_IORecursiveLockHaveLock':('IOKit/IOLocks.h','boolean_t(const IORecursiveLock*)','pointer64; boolean_t32','current thread ownership; reentry refusal'),
        '_ml_at_interrupt_context':('i386/machine_routines.h or arm/machine_routines.h','boolean_t(void)','boolean_t32 result','deny interrupt entry; not a complete sleepability certificate'),
        '_ml_get_interrupts_enabled':('i386/machine_routines.h or arm/machine_routines.h','boolean_t(void)','boolean_t32 result','deny disabled interrupts; cannot detect arbitrary caller spinlocks')}
    for arch,link in links.items():
        by_name={x['symbol']:x for x in symbols[arch]['per_symbol']}
        for name in link['remaining']:
            header,prototype,layout,risk=specs[name];row=by_name[name]
            demangled=subprocess.run(['xcrun','c++filt',name[1:] if name.startswith('__Z') else name],cwd=safe.ROOT,env=env,capture_output=True,text=True,timeout=15,check=True).stdout.strip()
            rows.append(dict(symbol=name,demangled=demangled,callers=row['users'],module='project CPU/native compile allowlist',header=header,prototype=prototype,parameter_layout=layout,
                architecture=arch,compiled_SDK=sdkversion,target_SDK='26.5 declared; binary absent',calling_convention='Apple kernel C++ / C target ABI; current SDK only',
                KPI_source_reference=row['reference'],source_reference_status='VERIFIED_EXPORT_REFERENCE',target_binary_status='UNVERIFIED',
                version_compatibility='BLOCKED: target binary/class ABI unavailable; SDK26 declarations verified',real_target_link_resolution='UNVERIFIED',risk=risk))
    safe.write('reports/m13/kpi-details.json',json.dumps(dict(pin=PIN,imports=rows,evidence_levels=dict(A='public source',B='current SDK declaration / target source header reference',C='pinned architecture export list',D='UNVERIFIED target binary',E='NOT RUN load/runtime')),indent=2))
    abi=json.loads(audit_path.read_text());abi['historical_SDK27_sizes']={arch:item['sizes'] for arch,item in json.loads(safe.checked('reports/m12/abi-audit.json').read_text())['current_SDK_layout'].items()};safe.write(audit_path,json.dumps(abi,indent=2))
    print(json.dumps(dict(class_comparisons=len(comparisons),import_records=len(rows),target_ABI='BLOCKED')))
if __name__=='__main__':main()
