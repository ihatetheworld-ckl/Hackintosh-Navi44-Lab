// Compiled with Core flags; no fake SDK, raw allocations or hardware calls.
#include "../../development/AMDRadeonRDNA4-Navi44/platform/darwin_contract.hpp"
#include "../../development/AMDRadeonRDNA4-Navi44/platform/contract.hpp"
static_assert(sizeof(NaviCore::Error)==1,"fixed error");
static_assert(alignof(NaviCore::Node)>=alignof(uint64_t),"typed scratch alignment");
NaviCore::Result contractCheck(NaviPlatform::Contract c){
    return NaviPlatform::validateSnapshot(c,Asic::Target::Gfx1200);
}
