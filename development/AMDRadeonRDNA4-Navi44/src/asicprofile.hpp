// Offline-only ASIC identities. New code under repository BSD-3-Clause LICENSE.
// LLVM 20.1.8 ELF.h commit 87f0227cb60147a26a1eeb4fb06e3b505e9c7261.
#ifndef Navi44AsicProfile_hpp
#define Navi44AsicProfile_hpp
#include <stdint.h>

namespace Asic {
enum class Target : uint8_t { Unknown = 0, Gfx1200 = 0x48, Gfx1201 = 0x4e };
enum class Family : uint8_t { Unknown, Navi44, Navi48 };
struct IpVersion { uint8_t major, minor, revision; bool known; };
struct Topology {
    bool verified;
    uint32_t se, cu, rb, tcc;
    uint64_t vramBytes, visibleBarBytes;
};
struct Profile {
    Family family;
    Target target;
    uint16_t vendor, device;
    uint8_t revision;
    bool revisionKnown;
    bool revisionVerified;
    uint32_t capabilities; // zero: no hardware feature has been verified
    IpVersion expectedGc;
    Topology topology;
};
inline Profile identify(uint16_t vendor, uint16_t device, uint8_t revision = 0,
                        bool revisionKnown = false) {
    Profile p { Family::Unknown, Target::Unknown, vendor, device, revision,
                revisionKnown, false, 0, {0, 0, 0, false}, {false, 0, 0, 0, 0, 0, 0} };
    if (vendor != 0x1002) return p;
    if (device == 0x7590) {
        p.family = Family::Navi44; p.target = Target::Gfx1200;
        p.expectedGc = {12, 0, 0, true}; // expected family, not a card capture
    }
    else if (device == 0x7550 || device == 0x7551) {
        p.family = Family::Navi48; p.target = Target::Gfx1201;
        p.expectedGc = {12, 0, 1, true};
    }
    return p;
}
// There is deliberately no hardware backend or override in this prototype.
constexpr bool hardwareInitializationAllowed() { return false; }
}
#endif
