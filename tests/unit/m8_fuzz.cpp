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
    auto didBase=M8Fixture::displayId1440p180();
    accepted=rejected=0;
    for(unsigned i=0;i<400;++i){
        auto raw=didBase;
        for(unsigned j=0,n=1+random()%4;j<n;++j)raw[128+random()%128]^=uint8_t(1+random()%255);
        if(i%3==0){
            uint8_t pay=raw[128+2];
            if(pay>0&&5u+pay<127u){
                uint8_t s=0;raw[128+5+pay]=0;
                for(size_t k=129;k<128+5+pay;++k)s=uint8_t(s+raw[k]);
                raw[128+5+pay]=uint8_t(0-s);
            }
            M8Fixture::seal(raw,128,128);
        }
        NaviDisplay::Mode modes[64]{};NaviDisplay::Monitor out{};
        auto r=NaviDisplay::edid({raw.data(),raw.size()},NaviDisplay::Origin::Synthetic,out,modes,64,NaviDisplay::ExtensionPolicy::AllowDisplayId);
        if((!r.ok()&&out.modeCount)||out.modeCount>64)return 1;
        for(size_t j=0;j<out.modeCount;++j)if(modes[j].hardwareVerified||!modes[j].refresh.denominator)return 1;
        r.ok()?++accepted:++rejected;
    }
    NaviCore::QueryCandidate qProj{};
    qProj.device.profile=Asic::identify(0x1002,0x7590,0xc0,true);
    qProj.device.present=7u;qProj.device.gcMajor=12;qProj.device.gcMinor=0;qProj.device.gcRevision=0;
    qProj.device.se=2;qProj.device.cu=32;qProj.device.rb=8;qProj.device.tcc=8;qProj.device.gbAddrConfig=0x243u;
    qProj.device.vramBytes=16ULL<<30;qProj.device.visibleBarBytes=16ULL<<30;
    qProj.provenance=NaviCore::Provenance::StaticReference;qProj.generation=99;
    std::array<uint8_t,192> wire192{};NaviCore::CobaltQueryProjection proj{};
    if(!NaviCore::projectToCobaltInfo(qProj,proj,wire192.data(),192).ok())return 1;
    size_t pAcc=0,pRej=0;
    for(unsigned i=0;i<400;++i){
        auto raw=wire192;
        for(unsigned j=0,n=1+random()%4;j<n;++j)raw[random()%192]^=uint8_t(1+random()%255);
        const size_t length=i%5==0?random()%192:192;
        NaviCore::CobaltQueryProjection out{};
        auto r=NaviCore::decodeCobaltProjection({raw.data(),length},out);
        if((!r.ok()&&out.generation)||(r.ok()&&(out.flags!=0||out.vramVisFree!=0||out.vramHiFree!=0||out.gfxTarget!=uint16_t(Asic::Target::Gfx1200))))return 1;
        r.ok()?++pAcc:++pRej;
    }
    std::cout<<"M9_EXT_FUZZ displayid_inputs=400 accepted="<<accepted<<" rejected="<<rejected
             <<" proj_inputs=400 proj_accepted="<<pAcc<<" proj_rejected="<<pRej<<" invariants=PASS\n";
}
