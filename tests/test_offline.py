"""Execute only our pure Python library, synthetic bytes and source assertions."""
import dataclasses
import ast
import importlib.util
import pathlib
import random
import struct
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
def load(name, path):
    import sys
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
n = load('navi44', ROOT/'development/AMDRadeonRDNA4-Navi44/host/navi44.py')
f = load('synthetic', ROOT/'tests/fixtures/synthetic.py')


class ProfileTests(unittest.TestCase):
    def test_navi44(self):
        p = n.identify(0x1002, 0x7590)
        self.assertEqual((p.asic, p.target), ('Navi44', n.Target.GFX1200))
        self.assertFalse(p.capabilities)
        self.assertFalse(p.revision_verified)
    def test_navi48_regression(self):
        for device in (0x7550, 0x7551):
            self.assertEqual(n.identify(0x1002, device).target, n.Target.GFX1201)
    def test_unknown_vendor(self):
        with self.assertRaises(n.Invalid): n.identify(0x1234, 0x7590)
    def test_unknown_device(self):
        with self.assertRaises(n.Invalid): n.identify(0x1002, 0xFFFF)
    def test_revision(self):
        self.assertEqual(n.identify(0x1002, 0x7590, 0).revision, 0)
        with self.assertRaises(n.Invalid): n.identify(0x1002, 0x7590, 256)
    def test_hardware_never_authorized(self):
        self.assertFalse(n.hardware_initialization_allowed(True))


class ParserTests(unittest.TestCase):
    def test_basic(self): self.assertEqual(len(n.parse_discovery(f.discovery()).ips), 5)
    def test_v2(self): self.assertEqual(n.parse_discovery(f.discovery(binary=2)).binary_version, (2, 0))
    def test_64bit(self):
        d = f.discovery(width=8, extra=((999, 0, (1, 0, 0), (0x100000000,)),))
        self.assertEqual(n.parse_discovery(d).ips[-1].bases[0], 0x100000000)
    def reject(self, mutate, error=None, tables=True):
        d = f.discovery()
        mutate(d)
        f.reseal(d, tables=tables)
        with self.assertRaises(n.Invalid) as ctx: n.parse_discovery(d)
        if error: self.assertIn(error, str(ctx.exception))
    def test_magic(self): self.reject(lambda d: d.__setitem__(0, 0), 'magic')
    def test_version(self): self.reject(lambda d: struct.pack_into('<H', d, 4, 9), 'version')
    def test_truncations(self):
        d = f.discovery()
        for end in range(len(d)):
            with self.assertRaises(n.Invalid): n.parse_discovery(d[:end])
    def test_length(self): self.reject(lambda d: struct.pack_into('<H', d, 10, 0xffff))
    def test_binary_checksum(self):
        d = f.discovery(); d[-1] ^= 1
        with self.assertRaisesRegex(n.Invalid, 'binary_checksum'): n.parse_discovery(d)
    def test_table_checksum(self): self.reject(lambda d: d.__setitem__(214, 13), 'table_checksum', False)
    def test_unknown_ip(self):
        d = n.parse_discovery(f.discovery(extra=((999, 0, (1,0,0), (10,)),)))
        self.assertEqual(d.unknown_ids, (999,))
    def test_duplicate(self):
        with self.assertRaisesRegex(n.Invalid, 'duplicate'):
            n.parse_discovery(f.discovery(extra=((11, 0, (12,0,1), (10,)),)))
    def test_die_offset(self): self.reject(lambda d: struct.pack_into('<H', d, 144, 1), 'die_offset')
    def test_address_overflow(self):
        with self.assertRaisesRegex(n.Invalid, 'overflow'):
            n.parse_discovery(f.discovery(width=8, extra=((999,0,(1,0,0),(0xffffffffffffffff,)),)))
    def test_integer_overflow(self):
        with self.assertRaises(n.Invalid): n.bounded(100, 0xffffffffffffffff, 2)
        with self.assertRaises(n.Invalid): n.bounded(100, 1 << 64, 0)
    def test_overlap(self): self.reject(lambda d: struct.pack_into('<H', d, 20, 128), 'overlap')
    def test_ip_version(self): self.reject(lambda d: struct.pack_into('<H', d, 132, 5), 'version')
    def test_base_count(self): self.reject(lambda d: d.__setitem__(215, 17), 'base_count')
    def test_gc_mismatch(self):
        with self.assertRaisesRegex(n.Invalid, 'mismatch'):
            n.validate_discovery(n.identify(0x1002,0x7590), n.parse_discovery(f.discovery(gc=(12,0,1))))
    def test_gc_unknown(self):
        with self.assertRaisesRegex(n.Invalid, 'topology_unknown'):
            n.validate_discovery(n.identify(0x1002,0x7590), n.parse_discovery(f.discovery(topology=False)))
    def test_navi48(self):
        self.assertTrue(n.validate_discovery(n.identify(0x1002,0x7550), n.parse_discovery(f.discovery(gc=(12,0,1)))))
    def test_mutation_robustness(self):
        rng = random.Random(7590)
        for _ in range(1000):
            d = f.discovery()
            for _ in range(rng.randrange(1, 5)): d[rng.randrange(len(d))] ^= rng.randrange(1,256)
            try: n.parse_discovery(d)
            except n.Invalid: pass
    @unittest.skip('No public verified RX9060XT IP Discovery capture; no hardware access authorized')
    def test_real_navi44_fixture(self): pass


class FirmwareTests(unittest.TestCase):
    def setUp(self):
        self.p = n.identify(0x1002,0x7590)
        self.d = n.parse_discovery(f.discovery())
        self.needs = n.firmware_requirements(self.p,self.d)
        self.blobs = [n.FirmwareBlob(x,f.firmware(x),'synthetic') for x in self.needs]
    def test_manifest(self): self.assertTrue(n.validate_firmware(self.needs,self.blobs))
    def test_missing(self):
        with self.assertRaisesRegex(n.Invalid,'missing'): n.validate_firmware(self.needs,self.blobs[:-1])
    def test_wrong_ip(self):
        b = bytearray(self.blobs[0].data); struct.pack_into('<H',b,12,99)
        self.blobs[0] = dataclasses.replace(self.blobs[0],data=bytes(b))
        with self.assertRaisesRegex(n.Invalid,'ip_mismatch'): n.validate_firmware(self.needs,self.blobs)
    def test_duplicate(self):
        with self.assertRaisesRegex(n.Invalid,'duplicate'): n.validate_firmware(self.needs,self.blobs+[self.blobs[0]])
    def test_bad_size(self):
        self.blobs[0] = dataclasses.replace(self.blobs[0],data=b'bad')
        with self.assertRaises(n.Invalid): n.validate_firmware(self.needs,self.blobs)
    def test_unknown_header(self):
        b=bytearray(self.blobs[0].data); struct.pack_into('<H',b,8,2)
        self.blobs[0]=dataclasses.replace(self.blobs[0],data=bytes(b))
        with self.assertRaisesRegex(n.Invalid,'version'): n.validate_firmware(self.needs,self.blobs)
    def test_crc_unverified(self):
        b=bytearray(self.blobs[0].data); struct.pack_into('<I',b,28,123)
        self.blobs[0]=dataclasses.replace(self.blobs[0],data=bytes(b))
        with self.assertRaisesRegex(n.Invalid,'crc_unverified'): n.validate_firmware(self.needs,self.blobs)
    def test_payload_inside_header(self):
        b=bytearray(self.blobs[0].data); struct.pack_into('<I',b,24,4)
        self.blobs[0]=dataclasses.replace(self.blobs[0],data=bytes(b))
        with self.assertRaises(n.Invalid): n.validate_firmware(self.needs,self.blobs)
    def test_state_machine(self):
        s=n.OfflineSession(); self.assertEqual(s.run(self.p,self.d,self.blobs),n.State.READY)
        self.assertFalse(n.hardware_initialization_allowed(s))
        with self.assertRaises(n.Invalid): s.run(self.p,self.d,self.blobs)
    def test_failed_cleanup(self):
        s=n.OfflineSession()
        with self.assertRaises(n.Invalid): s.run(self.p,self.d,[])
        self.assertEqual(s.state,n.State.FAILED); self.assertIsNotNone(s.error)
    def test_tampered_profile(self):
        with self.assertRaisesRegex(n.Invalid,'tampered'):
            n.OfflineSession().run(dataclasses.replace(self.p,capabilities=frozenset({'Metal'})),self.d,self.blobs)


class ElfTests(unittest.TestCase):
    def test_gfx1200(self): self.assertTrue(n.validate_elf(f.elf(),n.Target.GFX1200))
    def test_gfx1201_regression(self): self.assertTrue(n.validate_elf(f.elf(0x4e),n.Target.GFX1201))
    def test_cross_target(self):
        for machine,target in ((0x48,n.Target.GFX1201),(0x4e,n.Target.GFX1200)):
            with self.assertRaisesRegex(n.Invalid,'target'): n.validate_elf(f.elf(machine),target)
    def test_unknown(self):
        with self.assertRaises(n.Invalid): n.validate_elf(f.elf(),n.Target.UNKNOWN)
    def test_truncated(self):
        for size in range(64):
            with self.assertRaises(n.Invalid): n.validate_elf(f.elf()[:size],n.Target.GFX1200)
    def test_no_metadata(self):
        with self.assertRaisesRegex(n.Invalid,'metadata'): n.validate_elf(f.elf(metadata=False),n.Target.GFX1200)
    def test_empty_metadata(self):
        with self.assertRaisesRegex(n.Invalid,'metadata'): n.validate_elf(f.elf(metadata_value={}),n.Target.GFX1200)
    def test_missing_kernel_identity(self):
        with self.assertRaisesRegex(n.Invalid,'metadata'):
            n.validate_elf(f.elf(metadata_value={'amdhsa.version':[1,0],'amdhsa.kernels':[{}]}),n.Target.GFX1200)
    def test_overflow(self):
        d=f.elf(); struct.pack_into('<Q',d,32,0xffffffffffffffff)
        with self.assertRaises(n.Invalid): n.validate_elf(d,n.Target.GFX1200)
    def test_bad_magic(self):
        d=f.elf(); d[0]=0
        with self.assertRaises(n.Invalid): n.validate_elf(d,n.Target.GFX1200)
    @unittest.skip('No actual gfx1200 compiler output or macOS SDK; synthetic envelope is not shader validation')
    def test_real_shader(self): pass


class AbiTests(unittest.TestCase):
    def test_roundtrip(self):
        for dev in (0x7590,0x7550,0x7551):
            p=n.identify(0x1002,dev,0); self.assertEqual(n.decode_device_info(n.encode_device_info(p)),p)
    def test_caps_rejected(self):
        d=bytearray(n.encode_device_info(n.identify(0x1002,0x7590))); d[16]=1
        with self.assertRaises(n.Invalid): n.decode_device_info(d)
    def test_unknown_geometry(self):
        with self.assertRaises(n.Invalid): n.encode_device_info(n.identify(0x1002,0x7590),(2,2))
    def test_bad_version(self):
        d=bytearray(n.encode_device_info(n.identify(0x1002,0x7590))); d[4]=2
        with self.assertRaises(n.Invalid): n.decode_device_info(d)


class SafetyTests(unittest.TestCase):
    def test_host_imports_have_no_hardware_backend(self):
        tree=ast.parse((ROOT/'development/AMDRadeonRDNA4-Navi44/host/navi44.py').read_text(encoding='utf-8'))
        imported=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Import): imported.update(x.name for x in node.names)
            if isinstance(node,ast.ImportFrom): imported.add(node.module)
        self.assertTrue(imported <= {'dataclasses','enum','struct'})
    def test_build_excludes_hardware(self):
        text=(ROOT/'CMakeLists.txt').read_text(encoding='utf-8')
        executable=text.split('add_executable(',1)[1].split(')',1)[0]
        self.assertNotIn('device.cpp',executable); self.assertNotIn('plugin.cpp',executable)
        self.assertIn('codeobj.cpp',executable); self.assertIn('ipdiscovery.cpp',executable)
    def test_init_guard_precedes_hardware(self):
        text=(ROOT/'development/AMDRadeonRDNA4-Navi44/src/device.cpp').read_text(encoding='utf-8')
        init=text.split('bool RDNA4Device::init(',1)[1]
        self.assertLess(init.index('hardwareInitializationAllowed'),init.index('pciDevice = pci'))
        header=(ROOT/'development/AMDRadeonRDNA4-Navi44/src/asicprofile.hpp').read_text(encoding='utf-8')
        self.assertIn('hardwareInitializationAllowed() { return false; }',header)
    def test_pinned_llvm_constants(self):
        text=(ROOT/'upstream/references/llvm-ELF.h').read_text(encoding='utf-8')
        import re
        for label,target in (('GFX1200',n.Target.GFX1200),('GFX1201',n.Target.GFX1201)):
            match=re.search(r'EF_AMDGPU_MACH_AMDGCN_'+label+r'\s*=\s*(0x[0-9a-fA-F]+)',text)
            self.assertIsNotNone(match); self.assertEqual(int(match.group(1),16),target.value)


if __name__ == '__main__': unittest.main(verbosity=2)
