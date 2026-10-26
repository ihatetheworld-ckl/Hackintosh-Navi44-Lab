#include "display.hpp"
namespace NaviDisplay {
using namespace NaviCore;
namespace {
uint64_t gcd(uint64_t a,uint64_t b){while(b){uint64_t t=a%b;a=b;b=t;}return a;}
bool originValid(Origin o){return o==Origin::Unknown||o==Origin::Synthetic||o==Origin::StaticReference;}
Result add(const Edid::DetailedTiming&t,uint32_t source,Monitor&m,Mode*out,size_t cap){
    Mode candidate{};Result r=timing(t,candidate);if(!r.ok())return r;
    candidate.sources=source;candidate.sinkDeclared=true;
    for(size_t i=0;i<m.modeCount;++i){
        if(Edid::sameTiming(t,out[i].timing)){out[i].sources|=source;++m.duplicates;return success();}
        if(t.hActive==out[i].timing.hActive&&t.vActive==out[i].timing.vActive&&
           candidate.refresh.numerator==out[i].refresh.numerator&&candidate.refresh.denominator==out[i].refresh.denominator){
            out[i].sameRateAlternative=true;candidate.sameRateAlternative=true;
        }
    }
    if(m.modeCount==cap)return failure("display_mode_budget",Error::Budget);
    out[m.modeCount++]=candidate;return success();
}
Result parseEdid(View v,Origin origin,Monitor&m,Mode*out,size_t cap,ExtensionPolicy policy){
    if(!originValid(origin))return failure("display_origin");
    if(!v.data||v.size<128||v.size>Edid::MaxBlocks*128)return failure("edid_bounds",Error::Bounds);
    if(v.data[18]!=1||(v.data[19]!=3&&v.data[19]!=4))return failure("edid_version",Error::Unsupported);
    const size_t blocks=size_t(v.data[126])+1;
    if(blocks>Edid::MaxBlocks||v.size!=blocks*128)return failure("edid_extension_length",Error::Bounds);
    Edid::BaseInfo base{};if(!Edid::parseBaseBlock(v.data,128,base))return failure("edid_base");
    const uint16_t manufacturer=uint16_t(v.data[8])<<8|v.data[9];
    if(manufacturer&0x8000)return failure("edid_manufacturer");
    for(unsigned i=0;i<3;++i){
        const unsigned c=(manufacturer>>(10-5*i))&31;
        if(!c||c>26)return failure("edid_manufacturer");m.manufacturer[i]=char('A'+c-1);
    }
    m.product=uint16_t(v.data[10])|uint16_t(v.data[11])<<8;m.revision=base.revision;m.digital=base.digital;m.origin=origin;
    for(unsigned i=0;i<4;++i){
        const uint8_t*d=v.data+54+18*i;
        if(!(d[0]|d[1]))continue;
        // This milestone does not model stereo, borders, analog/composite sync or interlace.
        if(d[15]||d[16]||(d[17]&0x60)||(d[17]&0x18)!=0x18)return failure("edid_dtd_signal_unsupported",Error::Unsupported);
        Edid::DetailedTiming t{};if(!Edid::parseDetailedTiming(d,t))return failure("edid_dtd");
        Result r=add(t,BaseDtd,m,out,cap);if(!r.ok())return r;
    }
    // Avoid the legacy digital=>RB heuristic for EDID 1.3. No CVT/GTF synthesis.
    if(base.revision==3)base.reducedBlanking=false;
    for(size_t i=0;i<Edid::EstablishedCount;++i){
        Edid::DetailedTiming t{};
        if(Edid::establishedTiming(base,i,t)){Result r=add(t,Established,m,out,cap);if(!r.ok())return r;}
        else if(base.established[i/8]&(0x80>>(i%8)))++m.unresolvedTimings;
    }
    for(size_t i=0;i<Edid::StandardCount;++i){
        Edid::DetailedTiming t{};
        if(Edid::standardTiming(base,i,t)){Result r=add(t,Standard,m,out,cap);if(!r.ok())return r;}
        else if(base.standard[i][0]>1)++m.unresolvedTimings;
    }
    for(size_t b=1;b<blocks;++b){
        const uint8_t*ext=v.data+b*128;
        if(!Edid::blockChecksumOk(ext))return failure("edid_extension_checksum");
        if(ext[0]==0x70&&policy==ExtensionPolicy::AllowDisplayId){
            Edid::DisplayIdCaps did{};
            if(!Edid::parseDisplayIdBlock(ext,did))return failure("edid_displayid_structure");
            for(size_t i=0;i<did.timingCount;++i){
                Result r=add(did.timings[i],DisplayIdType1,m,out,cap);if(!r.ok())return r;
            }
            continue;
        }
        if(ext[0]!=2){
            if(policy!=ExtensionPolicy::KnownBlocksOnly)return failure("edid_extension_unsupported",Error::Unsupported);
            m.partial=true;continue;
        }
        Edid::CtaCaps cta{};if(!Edid::parseCtaBlock(ext,cta))return failure("edid_cta_structure");
        m.scdcAdvertised=m.scdcAdvertised||cta.scdcPresent;
        uint32_t max=cta.hfMaxTmdsKHz?cta.hfMaxTmdsKHz:cta.maxTmdsKHz;
        if(max>m.sinkMaxTmdsKHz)m.sinkMaxTmdsKHz=max;
        for(size_t i=0;i<cta.vicCount;++i){
            Edid::DetailedTiming t{};
            if(Edid::vicTiming(cta.vics[i],t)){Result r=add(t,CtaVic,m,out,cap);if(!r.ok())return r;}
            else ++m.unresolvedTimings;
        }
        for(size_t i=0;i<cta.dtdCount;++i){
            const uint8_t*d=ext+ext[2]+i*18;
            if(d[15]||d[16]||(d[17]&0x60)||(d[17]&0x18)!=0x18)return failure("edid_dtd_signal_unsupported",Error::Unsupported);
            Result r=add(cta.dtds[i],CtaDtd,m,out,cap);if(!r.ok())return r;
        }
        // Unknown vendor/extended blocks are not interpreted as link or color capabilities.
    }
    if(!m.modeCount)return failure("edid_modes_missing",Error::Missing);
    if(m.unresolvedTimings)m.partial=true;
    return success();
}
}
Result timing(const Edid::DetailedTiming&input,Mode&out){
    const Edid::DetailedTiming t=input; // Safe when input aliases out.timing.
    out={};
    if(t.interlaced)return failure("mode_interlace_unsupported",Error::Unsupported);
    if(!t.hActive||!t.vActive||!t.hBlank||!t.vBlank||!t.hSyncWidth||!t.vSyncWidth||
       uint32_t(t.hSyncOffset)+t.hSyncWidth>t.hBlank||uint32_t(t.vSyncOffset)+t.vSyncWidth>t.vBlank)
        return failure("mode_geometry");
    if(t.pixelClockKHz<1000||t.pixelClockKHz>2500000)return failure("mode_clock");
    const uint64_t numerator=uint64_t(t.pixelClockKHz)*1000,denominator=uint64_t(t.hTotal())*t.vTotal();
    if(numerator<denominator||numerator>denominator*1000)return failure("mode_rate");
    const uint64_t common=gcd(numerator,denominator);
    out.timing=t;out.refresh={numerator/common,denominator/common};return success();
}
Result edid(View v,Origin o,Monitor&out,Mode*storage,size_t capacity,ExtensionPolicy policy){
    out={};if(!storage||!capacity||capacity>MaxModes)return failure("display_storage",Error::Budget);
    for(size_t i=0;i<capacity;++i)storage[i]={};
    Monitor result{};Result r=parseEdid(v,o,result,storage,capacity,policy);
    if(!r.ok()){for(size_t i=0;i<capacity;++i)storage[i]={};return r;}
    out=result;return success();
}
Result connectors(View v,Origin origin,ConnectorList&out){
    out={};if(!originValid(origin))return failure("display_origin");
    AtomBios rom;if(!rom.init(v.data,v.size))return failure(rom.error());
    AtomBios::DisplayPath paths[AtomBios::MaxDisplayPaths]{};
    const size_t count=rom.getDisplayPaths(paths,AtomBios::MaxDisplayPaths);
    if(!count)return failure(rom.error()?rom.error():"connectors_missing",Error::Missing);
    ConnectorList result{};result.origin=origin;result.count=count;
    for(size_t i=0;i<count;++i){
        result.entries[i].path=paths[i];result.entries[i].type=AtomBios::connectorType(paths[i].connectorObjId);
        if(paths[i].recordOffset&&!rom.getPathRecords(paths[i],result.entries[i].records))return failure(rom.error());
        // Parsed ids describe board data, not verified PHY routing or live connectors.
    }
    out=result;return success();
}
Result boardDiagnostics(View v,Origin origin,BoardDiagnostics&out){
    out={};if(!originValid(origin))return failure("display_origin");
    AtomBios rom;if(!rom.init(v.data,v.size))return failure(rom.error());
    BoardDiagnostics result{};result.origin=origin;
    result.subsysVid=rom.subsystemVendorId();result.subsysId=rom.subsystemId();
    result.hasFirmwareInfo=rom.getFirmwareInfo(result.firmware);
    result.gpioPinCount=rom.getGpioPins(result.gpioPins,AtomBios::MaxGpioPins);
    out=result;return success();
}
Result assess(const Mode&m,const LinkBudget&link,const EngineBudget&engine,uint8_t bpp,Decision&out){
    out={};Mode canonical{};Result r=timing(m.timing,canonical);if(!r.ok())return r;
    if(m.refresh.numerator!=canonical.refresh.numerator||m.refresh.denominator!=canonical.refresh.denominator||m.hardwareVerified)
        return failure("mode_unverified_or_tampered");
    if(!originValid(link.origin)||!originValid(engine.origin)||(bpp!=24&&bpp!=30&&bpp!=36))return failure("link_format",Error::Unsupported);
    Decision d{};d.requiredBitsPerSecond=uint64_t(m.timing.pixelClockKHz)*1000*bpp;
    d.frameBytes=uint64_t(m.timing.hActive)*m.timing.vActive*4;
    if(d.frameBytes>UINT64_MAX/canonical.refresh.numerator)return failure("frame_rate_overflow",Error::Bounds);
    const uint64_t product=d.frameBytes*canonical.refresh.numerator;
    d.fullFrameBytesPerSecond=product/canonical.refresh.denominator+(product%canonical.refresh.denominator!=0);
    if(link.kind==LinkKind::Dp8b10b&&link.origin!=Origin::Unknown){
        if((link.lanes!=1&&link.lanes!=2&&link.lanes!=4)||
           (link.rateMbps!=1620&&link.rateMbps!=2700&&link.rateMbps!=5400&&link.rateMbps!=8100)||link.tmdsClockKHz)
            return failure("dp_budget");
        d.linkPayloadBitsPerSecond=uint64_t(link.rateMbps)*1000000*link.lanes*8/10;
        d.link=d.requiredBitsPerSecond<=d.linkPayloadBitsPerSecond?Fit::WithinBudget:Fit::Insufficient;
    }else if(link.kind==LinkKind::Tmds&&link.origin!=Origin::Unknown){
        if(link.lanes||link.rateMbps||!link.tmdsClockKHz||link.tmdsClockKHz>600000)return failure("tmds_budget");
        d.linkPayloadBitsPerSecond=uint64_t(link.tmdsClockKHz)*1000*24;
        d.link=d.requiredBitsPerSecond<=d.linkPayloadBitsPerSecond?Fit::WithinBudget:Fit::Insufficient;
    }else if(link.kind!=LinkKind::Unknown&&link.kind!=LinkKind::Dp8b10b&&link.kind!=LinkKind::Tmds)return failure("link_kind",Error::Unsupported);
    if(engine.origin!=Origin::Unknown&&engine.maxPixelClockKHz){
        if(engine.maxPixelClockKHz>2500000)return failure("engine_clock");
        d.engine=m.timing.pixelClockKHz<=engine.maxPixelClockKHz?Fit::WithinBudget:Fit::Insufficient;
    }
    out=d;return success();
}
}
