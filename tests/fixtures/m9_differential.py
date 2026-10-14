"""M9 CPU-only differential fixtures, BSD-3-Clause.

Migrates the reviewed M6.5 corpus/canonical/request and M7 extensions without
importing/executing historical runners or their report writers. All byte inputs
are synthetic; the existing invalid-strtab fixture is read-only and checked.
"""
from pathlib import Path
import importlib.util
import random
import struct
import sys
ROOT = Path(__file__).resolve().parents[2]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

n=load("m9logic",ROOT/"development/AMDRadeonRDNA4-Navi44/host/navi44.py")
f=load("m9fixture",ROOT/"tests/fixtures/synthetic.py")
extra=load("m9extras",ROOT/"tests/test_m7.py")


def base_canonical(mode,data,params=()):
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

def base_corpus():
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
    if not regression.is_file() or regression.read_bytes() != bytes(d):
        raise RuntimeError("Historical synthetic regression fixture missing or changed")
    cases += [('manifest',f.discovery(gc=gc),(device,)) for gc,device in
              (((12,0,0),0x7590),((12,0,1),0x7550),((12,0,1),0x7590))]
    cases += [('manifest',f.discovery(topology=False),(0x7590,))]
    return cases

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
        return base_canonical(mode,data,params)
    except n.Invalid as e:return {'ok':False,'error':str(e)}

def cases():
    result=base_corpus()
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
    raw=f.elf();struct.pack_into("<H",raw,56,5000)
    result.append(("elf",raw,(72,)))
    return result

all_cases=cases()

def fuzz_cases(count=2400):
    # Preserve M7's exact mutation seed set; the final case is M8's new budget check.
    rng=random.Random(759070);seeds=[x for x in all_cases[:-1] if len(x[1])>=32 and x[0] not in ('profile','elfbudget')]
    result=[]
    for i in range(count):
        mode,data,params=rng.choice(seeds);data=bytearray(data)
        for _ in range(rng.randrange(1,5)):data[rng.randrange(len(data))]^=rng.randrange(1,256)
        if mode=='discovery' and len(data)>=128 and i%2==0:
            if len(data)==struct.unpack_from('<H',data,10)[0] and struct.unpack_from('<H',data,4)[0] in (1,2):f.reseal(data)
        result.append((mode,data,params))
    return result
