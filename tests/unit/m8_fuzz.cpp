// Bounded deterministic parser mutation + invariants, not GPU/stress fuzzing.
#include "../../development/AMDRadeonRDNA4-Navi44/core/display.hpp"
#include "../../development/AMDRadeonRDNA4-Navi44/core/query_candidate.hpp"
#include "../fixtures/m8_display.hpp"
#include <iostream>
#include <vector>
int main(){
    uint32_t seed=759080;auto random=[&](){seed^=seed<<13;seed^=seed>>17;seed^=seed<<5;return seed;};
    size_t accepted=0,rejected=0;
    for(unsigned i=0;i<2400;++i){
        std::vector<uint8_t> input;
        if(i%2){auto a=M8Fixture::rom();input.assign(a.begin(),a.end());}
        else input=M8Fixture::cta((i%6)/2+1);
        for(unsigned j=0,n=1+random()%4;j<n;++j)input[random()%input.size()]^=uint8_t(1+random()%255);
        if(i%5==0)input.resize(random()%input.size());
        else if(i%3==0){
            if(i%2)M8Fixture::seal(input,0,input.size());
            else for(size_t off=0;off+128<=input.size();off+=128)M8Fixture::seal(input,off);
        }
        const auto original=input;NaviCore::Result result;
        if(i%2){
            NaviDisplay::ConnectorList out{};result=NaviDisplay::connectors({input.data(),input.size()},NaviDisplay::Origin::Synthetic,out);
            if((!result.ok()&&out.count)||out.count>8||out.boardVerified)return 1;
            for(size_t j=0;j<out.count;++j)if(out.entries[j].hardwareVerified||out.entries[j].routingKnown)return 1;
        }else{
            NaviDisplay::Mode modes[64]{};NaviDisplay::Monitor out{};
            result=NaviDisplay::edid({input.data(),input.size()},NaviDisplay::Origin::Synthetic,out,modes,64,NaviDisplay::ExtensionPolicy::KnownBlocksOnly);
            if((!result.ok()&&out.modeCount)||out.modeCount>64)return 1;
            for(size_t j=0;j<out.modeCount;++j){
                if(modes[j].hardwareVerified||!modes[j].refresh.denominator)return 1;
                const auto&t=modes[j].timing;
                if(modes[j].refresh.numerator*uint64_t(t.hTotal())*t.vTotal()!=
                   uint64_t(t.pixelClockKHz)*1000*modes[j].refresh.denominator)return 1;
            }
        }
        if(input!=original)return 1;
        result.ok()?++accepted:++rejected;
    }
    std::cout<<"M8_FUZZ seed=759080 inputs=2400 accepted="<<accepted<<" rejected="<<rejected<<" invariants=PASS\n";
    NaviCore::QueryCandidate query{};query.device.profile=Asic::identify(0x1002,0x7590);
    query.generation=1;query.provenance=NaviCore::Provenance::Synthetic;
    std::array<uint8_t,128> wire{};if(!NaviCore::encodeQuery(query,wire.data(),128).ok())return 1;
    accepted=rejected=0;
    for(unsigned i=0;i<800;++i){
        auto raw=wire;for(unsigned j=0,n=1+random()%4;j<n;++j)raw[random()%128]^=uint8_t(1+random()%255);
        const size_t length=i%4==0?random()%128:128;NaviCore::QueryCandidate out{};
        auto result=NaviCore::decodeQuery({raw.data(),length},out);
        if((!result.ok()&&out.generation)||(result.ok()&&out.device.profile.capabilities))return 1;
        result.ok()?++accepted:++rejected;
    }
    std::cout<<"M8_QUERY_FUZZ inputs=800 accepted="<<accepted<<" rejected="<<rejected<<" invariants=PASS\n";
}
