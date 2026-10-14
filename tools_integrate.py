"""Reviewed local-only edits; never executes upstream code or invokes tools."""
from pathlib import Path
import json
ROOT = Path(__file__).resolve().parent
DEV = ROOT / 'development/AMDRadeonRDNA4-Navi44'


def edit(path, before, after):
    p=DEV/path
    text=p.read_text(encoding='utf-8')
    if before not in text:
        raise RuntimeError('Unexpected upstream: '+path)
    p.write_text(text.replace(before,after),encoding='utf-8',newline='\n')


edit('src/codeobj.hpp','#include <stdint.h>','#include <stdint.h>\n#include "asicprofile.hpp"')
edit('src/codeobj.hpp','const char **why);','const char **why, Asic::Target expected = Asic::Target::Gfx1201);')
edit('src/codeobj.cpp','constexpr uint32_t kMachGfx1201 = 0x4e;', 'constexpr uint32_t kMachGfx1201 = 0x4e;')  # guarded source fingerprint
edit('src/codeobj.cpp','const char *checkHeader(const uint8_t *d, size_t n, Elf &e)',
     'const char *checkHeader(const uint8_t *d, size_t n, Elf &e, Asic::Target expected)')
edit('src/codeobj.cpp','if ((u32(d + 48) & 0xff) != kMachGfx1201)\n\t\treturn "not built for gfx1201";',
     'if (expected != Asic::Target::Gfx1200 && expected != Asic::Target::Gfx1201)\n\t\treturn "unknown expected target";\n\tif ((u32(d + 48) & 0xff) != static_cast<uint32_t>(expected))\n\t\treturn "AMDGPU target mismatch";')
edit('src/codeobj.cpp','const char **why) {','const char **why, Asic::Target expected) {')
edit('src/codeobj.cpp','checkHeader(d, n, e)','checkHeader(d, n, e, expected)')
edit('src/codeobj.cpp','va < addr + size','va - addr < size')
edit('src/codeobj.cpp','out = Kernel {};','out = Kernel {};\n\tif (!name) return fail("missing kernel name");')

# Preserve GPU initialization behavior for Navi48; explicitly refuse Navi44 at
# the existing match hook. No Info.plist match expansion or new hardware calls.
edit('src/plugin.cpp','#include "device.hpp"','#include "device.hpp"\n#include "asicprofile.hpp"')
edit('src/plugin.cpp','if (vendor == 0x1002 && (device == 0x7550 || device == 0x7551))',
     'const auto profile = Asic::identify(vendor, device);\n\t// Identification is not authorization. Navi44 stays outside every GPU hook.\n\tif (profile.family == Asic::Family::Navi44)\n\t\treturn false;\n\tif (profile.family == Asic::Family::Navi48)')

# Harden existing allocation-free parser. It deliberately rejects the 64-bit
# format: IpEntry exposes uint32_t bases. Full-width host parser is separate.
edit('src/ipdiscovery.hpp','size_t dieBase { 0 };',
     'size_t dieBase { 0 };\n\tsize_t binEnd { 0 }, ipEnd { 0 };')
edit('src/ipdiscovery.cpp','if (off + 2 > size)', 'if (off > size || 2 > size - off)')
edit('src/ipdiscovery.cpp','if (off + 4 > size)', 'if (off > size || 4 > size - off)')
edit('src/ipdiscovery.cpp','if (binSize < 16 || offset + binSize > size)',
     'if (offset > size || binSize < 60 || binSize > size - offset ||\n\t    (vmajor != 1 && vmajor != 2))')
edit('src/ipdiscovery.cpp','size_t ipd = offset + ipdOffset;',
     'const size_t listBytes = vmajor == 1 ? 48 : 0;\n\tuint16_t tableCount = 6;\n\tif (vmajor == 2 && (!readU16(offset + 12, tableCount) || !tableCount || tableCount > 6)) return false;\n\tconst size_t headerBytes = (vmajor == 1 ? 12 : 16) + (vmajor == 1 ? listBytes : 8u * tableCount);\n\tif (headerBytes > binSize || ipdOffset < headerBytes || ipdOffset > binSize || ipdSize > binSize - ipdOffset) return false;\n\tuint16_t tableSum;\n\tif (!readU16(tableList + 2, tableSum)) return false;\n\tuint16_t actualSum = 0;\n\tfor (size_t i = offset + ipdOffset; i < offset + ipdOffset + ipdSize; ++i) actualSum = static_cast<uint16_t>(actualSum + data[i]);\n\tif (actualSum != tableSum) return false;\n\tsize_t ipd = offset + ipdOffset;')
edit('src/ipdiscovery.cpp','numDies == 0)', 'numDies != 1)')
edit('src/ipdiscovery.cpp','// Single-die parts only (true for all dGPUs); die_info[0] at +14.',
     'uint16_t ipVersion, declaredSize;\n\tif (!readU16(ipd + 4, ipVersion) || (ipVersion != 3 && ipVersion != 4) ||\n\t    !readU16(ipd + 6, declaredSize) || declaredSize != ipdSize || data[ipd + 78] || data[ipd + 79]) return false;\n\t// Legacy 32-bit API: reject 64-bit encoding instead of truncation.')
edit('src/ipdiscovery.cpp','dieOffset == 0)',
     'dieOffset < ipdOffset + 80 || dieOffset > binSize || 4 > binSize - dieOffset)')
edit('src/ipdiscovery.cpp','binBase = offset;',
     'const size_t tableEnd = ipd + ipdSize;\n\tif (die < ipd + 80 || die > tableEnd || 4 > tableEnd - die) return false;\n\tsize_t p = die + 4;\n\tfor (uint16_t i = 0; i < nips; ++i) {\n\t\tif (p > tableEnd || 8 > tableEnd - p) return false;\n\t\tconst uint8_t count = data[p + 3];\n\t\tif (!count || count > MaxBases || 4u * count > tableEnd - p - 8) return false;\n\t\tsize_t q = die + 4;\n\t\tfor (uint16_t j = 0; j < i; ++j) {\n\t\t\tif (data[p] == data[q] && data[p + 1] == data[q + 1] && data[p + 2] == data[q + 2]) return false;\n\t\t\tq += 8 + 4u * data[q + 3];\n\t\t}\n\t\tp += 8 + 4u * count;\n\t}\n\tbinEnd = offset + binSize;\n\tipEnd = tableEnd;\n\tbinBase = offset;')
edit('src/ipdiscovery.cpp','valid = false;','valid = false;\n\tnumIps = 0; binBase = dieBase = binEnd = ipEnd = 0;')
edit('src/ipdiscovery.cpp','const size_t gc = binBase + tblOff;',
     'uint16_t gcSize, gcCheck;\n\tif (!readU16(tableList + 12, gcSize) || !readU16(tableList + 10, gcCheck) ||\n\t    tblOff > binEnd - binBase || gcSize > binEnd - binBase - tblOff || gcSize < 28) return false;\n\tconst size_t gc = binBase + tblOff;\n\tif (gc < ipEnd && gc + gcSize > dieBase) return false;\n\tuint16_t sum = 0;\n\tfor (size_t i = gc; i < gc + gcSize; ++i) sum = static_cast<uint16_t>(sum + data[i]);\n\tif (sum != gcCheck) return false;\n\tuint32_t declaredGc;\n\tif (!readU32(gc + 8, declaredGc) || declaredGc != gcSize) return false;')
edit('src/ipdiscovery.cpp','(gcMajor != 1 && gcMajor != 2))',
     '(gcMajor != 1 && gcMajor != 2) || gcMinor != 0 || gcSize < (gcMajor == 1 ? 88 : 80))')
edit('src/ipdiscovery.cpp','numSe = se;', 'if (!se || !rb) return false;\n\tnumSe = se;')
edit('src/ipdiscovery.cpp','byteOffset = (ip.bases[segment] + regDwordOffset) * 4;',
     'const uint64_t off = (static_cast<uint64_t>(ip.bases[segment]) + regDwordOffset) * 4;\n\tif (off > UINT32_MAX) return false;\n\tbyteOffset = static_cast<uint32_t>(off);')
print('Integrated profile gate, parameterized code objects and legacy parser checks')
