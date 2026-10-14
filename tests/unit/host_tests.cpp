// New code: BSD-3-Clause. Pure CPU test; no GPU/IOKit links.
#include "asicprofile.hpp"
#include "codeobj.hpp"
#include "ipdiscovery.hpp"
#include "offlinefirmware.hpp"
#include <assert.h>
#include <stdint.h>
int main() {
    using namespace Asic;
    assert(identify(0x1002, 0x7590).target == Target::Gfx1200);
    assert(identify(0x1002, 0x7550).target == Target::Gfx1201);
    assert(identify(0x1002, 0x7551).family == Family::Navi48);
    assert(identify(0x1234, 0x7590).family == Family::Unknown);
    assert(identify(0x1002, 0xffff).family == Family::Unknown);
    assert(!hardwareInitializationAllowed());
    uint8_t bad[512] {};
    IpDiscovery parser;
    assert(!parser.init(nullptr, 512));
    assert(!parser.init(bad, sizeof(bad)));
    assert(!parser.isValid());
    CodeObj::Image image {};
    const char *why = nullptr;
    assert(!CodeObj::parseImage(bad, sizeof(bad), image, &why, Target::Gfx1200));
    assert(!CodeObj::parseImage(bad, sizeof(bad), image, &why));
    assert(!CodeObj::parseImage(bad, sizeof(bad), image, &why, Target::Unknown));
    CodeObj::Kernel kernel {};
    assert(!CodeObj::findKernel(bad, sizeof(bad), nullptr, kernel, &why));
    OfflineFirmware::Need need { 12, 0, "synthetic" };
    assert(OfflineFirmware::validate(nullptr, 0, need) == OfflineFirmware::Error::Missing);
    assert(OfflineFirmware::validate(bad, sizeof(bad), need) != OfflineFirmware::Error::None);
    return 0;
}
