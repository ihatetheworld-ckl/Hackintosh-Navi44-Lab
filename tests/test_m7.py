"""M7 Python behavior regressions; all fixtures synthetic, CPU-only."""
import importlib.util,pathlib,sys,struct,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
n=load('m7n',ROOT/'development/AMDRadeonRDNA4-Navi44/host/navi44.py')
f=load('m7f',ROOT/'tests/fixtures/synthetic.py')
def package(minor=0):
    base=40 if minor else 36;header=base+32;data=bytearray(header+8)
    struct.pack_into('<IIHHHHIIII',data,0,len(data),header,2,minor,14,0,0,8,header,0)
    struct.pack_into('<I',data,32,2)
    struct.pack_into('<IIII',data,base,1,1,0,4);struct.pack_into('<IIII',data,base+16,2,1,4,4)
    data[header:]=b'TESTDATA';return data
def abi2(device=0x7590,present=0):
    data=bytearray(96);data[:4]=b'N44I';struct.pack_into('<HHHH',data,4,2,96,0x1002,device)
    struct.pack_into('<H',data,14,0x48 if device==0x7590 else 0x4e);struct.pack_into('<I',data,16,present)
    struct.pack_into('<I',data,64,1)
    if present&1:data[24:27]=bytes((12,0,0 if device==0x7590 else 1))
    if present&2:struct.pack_into('<IIIII',data,28,2,4,2,2,0x100) # synthetic only
    if present&4:struct.pack_into('<QQ',data,48,1024,512) # synthetic byte capacities
    return data

def relocation(allocated=False):
    """Non-executed synthetic ELF with an extra RELA table; never real shader code."""
    data=f.kernel_elf()
    # New section-header slot 6 overlaps the old NOTE placement at 608.
    # Relocate that NOTE before adding the header; do not relax parser bounds.
    length=struct.unpack_from('<Q',data,192+64+32)[0]
    data.extend(data[608:608+length]);struct.pack_into('<Q',data,192+64+24,1200)
    struct.pack_into('<H',data,60,7)
    struct.pack_into('<IIQQQQIIQQ',data,192+6*64,0,4,int(allocated)*2,0,1088,24,5,2,8,24)
    struct.pack_into('<QQq',data,1088,0,1<<32,0)
    return data
class M7(unittest.TestCase):
    def test_package20(self):self.assertFalse(n.parse_psp_package(package())['signature_verified'])
    def test_package21(self):self.assertEqual(len(n.parse_psp_package(package(1))['parts']),2)
    def test_package_duplicate(self):
        d=package();struct.pack_into('<I',d,52,1)
        with self.assertRaisesRegex(n.Invalid,'duplicate'):n.parse_psp_package(d)
    def test_package_overlap(self):
        d=package();struct.pack_into('<I',d,60,2)
        with self.assertRaisesRegex(n.Invalid,'overlap'):n.parse_psp_package(d)
    def test_package_unknown_version(self):
        d=package();struct.pack_into('<H',d,10,9)
        with self.assertRaisesRegex(n.Invalid,'version'):n.parse_psp_package(d)
    def test_package_aux_unverified(self):
        d=package(1);struct.pack_into('<I',d,36,1)
        with self.assertRaisesRegex(n.Invalid,'aux'):n.parse_psp_package(d)
    def test_package_crc_unverified(self):
        d=package();struct.pack_into('<I',d,28,1)
        with self.assertRaisesRegex(n.Invalid,'crc'):n.parse_psp_package(d)
    def test_abi2_unknown(self):self.assertEqual(n.decode_device_info_v2(abi2())['present'],0)
    def test_abi2_present_not_verified(self):self.assertEqual(n.decode_device_info_v2(abi2(present=7))['capabilities'],0)
    def test_abi2_navi48(self):self.assertEqual(n.decode_device_info_v2(abi2(0x7550,1))['target'],0x4e)
    def test_abi2_reserved(self):
        d=abi2();d[95]=1
        with self.assertRaisesRegex(n.Invalid,'reserved'):n.decode_device_info_v2(d)
    def test_abi2_false_capability(self):
        d=abi2();d[20]=1
        with self.assertRaisesRegex(n.Invalid,'header'):n.decode_device_info_v2(d)
    def test_abi2_unknown_topology(self):
        d=abi2();d[28]=1
        with self.assertRaisesRegex(n.Invalid,'unknown_topology'):n.decode_device_info_v2(d)
    def test_discovery_table_reserved(self):
        d=f.discovery();d[18]=1;f.reseal(d)
        with self.assertRaisesRegex(n.Invalid,'table_reserved'):n.parse_discovery(d)
    def test_discovery_binary_reserved(self):
        d=f.discovery(binary=2);d[14]=1;f.reseal(d)
        with self.assertRaisesRegex(n.Invalid,'binary_reserved'):n.parse_discovery(d)
    def test_metadata_caller_budget(self):
        with self.assertRaisesRegex(n.Invalid,'budget'):n.decode_metadata(f.msgpack({'x':1}),node_budget=1)
    def test_elf_nonalloc_relocation_structure(self):n.validate_elf(relocation(),n.Target.GFX1200)
    def test_elf_alloc_relocation_rejected(self):
        with self.assertRaisesRegex(n.Invalid,'relocations_unsupported'):n.validate_elf(relocation(True),n.Target.GFX1200)
    def test_elf_relocation_symbol_index(self):
        data=relocation();struct.pack_into('<Q',data,1096,3<<32)
        with self.assertRaisesRegex(n.Invalid,'relocations_invalid'):n.validate_elf(data,n.Target.GFX1200)
    def test_elf_relocation_entry_size(self):
        data=relocation();struct.pack_into('<Q',data,192+6*64+56,8)
        with self.assertRaisesRegex(n.Invalid,'relocations_invalid'):n.validate_elf(data,n.Target.GFX1200)
    def test_elf_symbol_link(self):
        data=f.kernel_elf();struct.pack_into('<I',data,192+5*64+40,1)
        with self.assertRaisesRegex(n.Invalid,'symbols_invalid'):n.validate_elf(data,n.Target.GFX1200)
    def test_elf_symbol_stride(self):
        data=f.kernel_elf();struct.pack_into('<Q',data,192+5*64+56,8)
        with self.assertRaisesRegex(n.Invalid,'symbols_invalid'):n.validate_elf(data,n.Target.GFX1200)
if __name__=='__main__':unittest.main(verbosity=2)
