"""One-time checked move of the existing advisory manifest/state into Core."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m7_safety as safe
base=safe.ROOT/'development/AMDRadeonRDNA4-Navi44'
source=base/'src/offlinevalidation.cpp'
text=source.read_text(encoding='utf-8');start=text.index('bool Offline::firmwareRequirements')
body=text[start:]
if 'struct Part' not in body or 'Advisory structural requirements' not in body:
    raise SystemExit('Manifest already moved or source differs; refusing reapplication')
body=body.replace('bool Offline::firmwareRequirements','NaviCore::Result NaviCore::firmwareRequirements')
body=body.replace('FirmwareRequirement (&out)[16], size_t &count, const char **why)',
                  'FirmwareRequirement (&out)[16], size_t &count)')
body=body.replace('count = 0;\n    auto fail = [&](const char *w) { count = 0; if (why) *why = w; return false; };',
                  'count = 0;\n    for (auto &entry : out) entry = {};\n    auto fail = [&](const char *w) { count = 0; for (auto &entry : out) entry = {}; return failure(w); };')
body=body.replace('    if (why) *why = nullptr;\n    return true;', '    return success();')
validation=base/'core/validation.cpp'
safe.write(validation,validation.read_text(encoding='utf-8')+'\n'+body)
safe.write(source,text[:start]+'''bool Offline::firmwareRequirements(const Asic::Profile&p,const IpDiscovery&d,
                                  FirmwareRequirement (&out)[16],size_t&count,const char**why){
    return NaviHost::result(NaviCore::firmwareRequirements(p,d,out,count),why);
}
''')
header=base/'src/offlinevalidation.hpp';text=header.read_text(encoding='utf-8')
text=text.replace('#include "ipdiscovery.hpp"','#include "ipdiscovery.hpp"\n#include "../core/model.hpp"')
text=text.replace('struct FirmwareRequirement { const char *block, *component; Asic::IpVersion ip; };',
                  'using FirmwareRequirement = NaviCore::FirmwareRequirement;')
start=text.index('enum class State');end=text.index('\n}\n#endif',start)
text=text[:start]+'using State = NaviCore::State;\nusing Session = NaviCore::Session;'+text[end:]
safe.write(header,text)
