"""M6.5 additional Python regression tests, CPU-only synthetic inputs."""
import importlib.util, pathlib, sys, struct, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m
n=load('m65logic',ROOT/'development/AMDRadeonRDNA4-Navi44/host/navi44.py')
f=load('m65data',ROOT/'tests/fixtures/synthetic.py')
class Additional(unittest.TestCase):
    def test_full_descriptor(self): self.assertTrue(n.validate_kernel(f.kernel_elf(),n.Target.GFX1200))
    def test_full_descriptor_navi48(self): self.assertTrue(n.validate_kernel(f.kernel_elf(0x4e),n.Target.GFX1201))
    def test_descriptor_kernarg_mismatch(self):
        d=f.kernel_elf();struct.pack_into('<I',d,840,9)
        with self.assertRaisesRegex(n.Invalid,'mismatch'): n.validate_kernel(d,n.Target.GFX1200)
    def test_descriptor_group_mismatch(self):
        d=f.kernel_elf();struct.pack_into('<I',d,832,17)
        with self.assertRaisesRegex(n.Invalid,'mismatch'): n.validate_kernel(d,n.Target.GFX1200)
    def test_descriptor_entry_underflow(self):
        d=f.kernel_elf();struct.pack_into('<q',d,848,-0x2000)
        with self.assertRaisesRegex(n.Invalid,'invalid'): n.validate_kernel(d,n.Target.GFX1200)
    def test_missing_symbol(self):
        d=f.kernel_elf();d[1060]=0
        with self.assertRaisesRegex(n.Invalid,'invalid'): n.validate_kernel(d,n.Target.GFX1200)
    def test_kernel_metadata_missing(self):
        with self.assertRaises(n.Invalid): n.validate_kernel(f.elf(),n.Target.GFX1200)
    def test_all_section_bounds(self):
        d=f.kernel_elf();struct.pack_into('<Q',d,192+4*64+24,0xffffffffffffffff)
        with self.assertRaises(n.Invalid): n.validate_elf(d,n.Target.GFX1200)
    def test_strtab_prevalidated_regression(self):
        d=f.kernel_elf(0x4e);d[486]=230
        with self.assertRaisesRegex(n.Invalid,'out_of_bounds'): n.validate_kernel(d,n.Target.GFX1201)
    def test_unknown_metadata_version(self):
        with self.assertRaisesRegex(n.Invalid,'unsupported'):
            n.validate_elf(f.elf(metadata_value={'amdhsa.version':[99,0],'amdhsa.kernels':[]}),n.Target.GFX1200)
    def test_component_type(self):
        need=n.FirmwareNeed('gc',(12,0,0),'not-an-amd-component')
        with self.assertRaisesRegex(n.Invalid,'component'):
            n.validate_firmware([need],[n.FirmwareBlob(need,f.firmware(need),'synthetic')])
if __name__=='__main__':unittest.main(verbosity=2)
