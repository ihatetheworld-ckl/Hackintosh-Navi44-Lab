// N44Q 1.0 candidate envelope over N44I v2. NOT production N48N or hardware authority.
#ifndef Navi44QueryCandidate_hpp
#define Navi44QueryCandidate_hpp
#include "device_info.hpp"
namespace NaviCore {
enum class Provenance:uint8_t { Unknown,Synthetic,StaticReference };
struct QueryCandidate {DeviceInfo device{};Provenance provenance{Provenance::Unknown};uint64_t generation{0};};
constexpr size_t QueryCandidateSize=128;
Result decodeQuery(View,QueryCandidate&);
Result encodeQuery(const QueryCandidate&,uint8_t*,size_t);
class OfflineOwner {
    QueryCandidate current{};uint64_t lastGeneration{0};bool active{false},leased{false},failed{false};
public:
    Result prepare(const QueryCandidate&);
    Result borrow(QueryCandidate&);
    Result giveBack(uint64_t generation);
    void close(){active=false;leased=false;current={};}
    bool canInitializeHardware()const{return false;}
};
}
#endif
