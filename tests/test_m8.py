"""New cross-language ELF resource budgets; fixtures stay synthetic."""
import importlib.util,pathlib,sys,struct,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
n=load('m8n',ROOT/'development/AMDRadeonRDNA4-Navi44/host/navi44.py')
f=load('m8f',ROOT/'tests/fixtures/synthetic.py')
class M8(unittest.TestCase):
    def test_elf_input_budget(self):
        with self.assertRaisesRegex(n.Invalid,'elf_input_budget'):n.validate_elf(bytes((16<<20)+1),n.Target.GFX1200)
    def test_elf_table_budget(self):
        b=f.elf();struct.pack_into('<H',b,56,5000)
        with self.assertRaisesRegex(n.Invalid,'elf_table_budget'):n.validate_elf(b,n.Target.GFX1200)
if __name__=='__main__':unittest.main(verbosity=2)
