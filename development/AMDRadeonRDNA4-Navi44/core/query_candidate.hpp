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

// Candidate mapping from verified N44Q 1.0 (128B) to a 192B Cobalt/RADV
// query-info wire layout. Never uses raw memcpy(192, 128) and never fabricates
// Navi48/gfx1201 canned values when fields are absent from the N44I presence
// mask. Hardware/boot status flags remain strictly zero in CPU-only mode.
constexpr size_t CobaltQueryInfoSize=192;
struct CobaltQueryProjection {
    uint32_t abiVersion{0},kextBuild{0},flags{0},vmid{0};
    uint32_t gbAddrConfig{0},gcVersion{0},ringSizeDw{0},maxIbs{0};
    uint64_t vramVisTotal{0},vramVisFree{0},vramHiTotal{0},vramHiFree{0};
    uint64_t gttCap{0},gttUsed{0},gttMaxBo{0},ptCap{0},ptUsed{0};
    uint64_t seqEmitted{0},seqRetired{0};
    uint64_t vaLowFirst{0},vaLowLast{0},vaHighFirst{0},vaHighLast{0};
    uint32_t maxBos{0},fenceSlots{0};
    uint16_t vendorId{0},deviceId{0},gfxTarget{0};
    uint8_t revisionId{0},provenance{0};
    uint32_t presenceMask{0},ownerPolicy{0};
    uint64_t generation{0};
};
Result projectToCobaltInfo(const QueryCandidate&,CobaltQueryProjection&,uint8_t*wire192=nullptr,size_t wireLen=0);
Result decodeCobaltProjection(View,CobaltQueryProjection&);
}
#endif
