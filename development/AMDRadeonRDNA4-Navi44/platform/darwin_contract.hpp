// FUTURE DARWIN BUILD interface; no counterfeit Apple SDK/types or hardware.
#ifndef Navi44DarwinContract_hpp
#define Navi44DarwinContract_hpp
#include "contract.hpp"
namespace NaviDarwin {
// Future macOS-only implementation must pair actual IOMalloc/IOFree and IOLog,
// respect kext lifetime, and provide stable CPU snapshots. No implementation here.
struct AdapterDraft {
    NaviPlatform::Contract callbacks;
    bool appleSdkValidated{false};
    bool hardwareInitializationAllowed()const{return false;}
};
static_assert(sizeof(uintptr_t)==8,"future x86_64 build model");
}
#endif
