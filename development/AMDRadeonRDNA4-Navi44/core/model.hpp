// Existing M6.5 advisory manifest/state, now shared Core. BSD-3-Clause.
#ifndef Navi44CoreModel_hpp
#define Navi44CoreModel_hpp
#include "validation.hpp"
#include "../src/ipdiscovery.hpp"
namespace NaviCore {
struct FirmwareRequirement { const char *block,*component;Asic::IpVersion ip; };
Result firmwareRequirements(const Asic::Profile&,const IpDiscovery&,
                            FirmwareRequirement (&out)[16],size_t&count);
enum class State:uint8_t { Unknown,PciMatched,ProfileValidated,DiscoveryValidated,
                          FirmwareRequirementsValidated,OfflineReady,Failed };
class Session {
public:
    State state{State::Unknown};
    bool advance(State next){
        if(state==State::Failed||state==State::OfflineReady)return false;
        if(next==State::Failed){state=next;return true;}
        if(static_cast<unsigned>(next)!=static_cast<unsigned>(state)+1){state=State::Failed;return false;}
        state=next;return true;
    }
};
static_assert(sizeof(State)==1,"fixed state representation; never wire-cast");
}
#endif
