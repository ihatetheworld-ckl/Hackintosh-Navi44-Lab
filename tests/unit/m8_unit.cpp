// CPU behavioral tests against fixed format expectations, never a GPU.
#include "../../development/AMDRadeonRDNA4-Navi44/core/display.hpp"
#include "../../development/AMDRadeonRDNA4-Navi44/core/integrity.hpp"
#include "../../development/AMDRadeonRDNA4-Navi44/core/query_candidate.hpp"
#include "../../development/AMDRadeonRDNA4-Navi44/host/platform_mock.hpp"
#include "../fixtures/m8_display.hpp"
#include <iostream>
#include <cstring>
int main(){
    using namespace NaviDisplay;using namespace NaviCore;using namespace M8Fixture;
    unsigned pass=0,fail=0;auto check=[&](const char*n,bool ok){std::cout<<(ok?"PASS ":"FAIL ")<<n<<'\n';ok?++pass:++fail;};
    Mode modes[64]{};Monitor monitor{};auto data=M8Fixture::edid();
    auto parse=[&](const auto&b,ExtensionPolicy p=ExtensionPolicy::RejectUnknown){return NaviDisplay::edid({b.data(),b.size()},Origin::Synthetic,monitor,modes,64,p);};
    check("edid_valid_14",parse(data).ok()&&monitor.modeCount==1&&std::strcmp(monitor.manufacturer,"NVI")==0&&monitor.product==44);
    check("edid_refresh_exact",modes[0].timing.hActive==1920&&modes[0].timing.vActive==1080&&modes[0].refresh.numerator==60&&modes[0].refresh.denominator==1&&!modes[0].hardwareVerified);
    data[19]=3;seal(data);check("edid_valid_13",parse(data).ok());data=M8Fixture::edid();
    data[0]=1;seal(data);check("edid_header_reject",!parse(data).ok()&&monitor.modeCount==0&&modes[0].sources==0);
    data=M8Fixture::edid();data[10]^=1;check("edid_checksum_reject",!parse(data).ok());
    data=M8Fixture::edid();bool truncated=true;for(size_t n=0;n<128;++n)truncated&=!NaviDisplay::edid({data.data(),n},Origin::Synthetic,monitor,modes,64).ok();
    check("edid_all_base_truncations",truncated);
    data[19]=5;seal(data);check("edid_unknown_revision",!parse(data).ok());data=M8Fixture::edid();
    data[126]=1;seal(data);check("edid_missing_extension",!parse(data).ok());data=M8Fixture::edid();
    data[8]=0;data[9]=0;seal(data);check("edid_manufacturer_invalid",!parse(data).ok());data=M8Fixture::edid();
    data[62]=255;data[63]=255;seal(data);check("edid_sync_outside_blank",!parse(data).ok());data=M8Fixture::edid();
    data[54]=1;data[55]=0;seal(data);check("edid_clock_too_small",!parse(data).ok());data=M8Fixture::edid();
    data[56]=0;data[58]&=15;seal(data);check("edid_zero_width",!parse(data).ok());data=M8Fixture::edid();
    data[71]|=0x80;seal(data);check("edid_interlace_unsupported",!parse(data).ok());data=M8Fixture::edid();
    data[71]|=0x20;seal(data);check("edid_stereo_unsupported",!parse(data).ok());data=M8Fixture::edid();
    for(unsigned i=0;i<18;++i)data[72+i]=data[54+i];seal(data);
    check("edid_duplicate_coalesced",parse(data).ok()&&monitor.modeCount==1&&monitor.duplicates==1);
    auto ext=cta();check("cta_vic_deduplicated",parse(ext).ok()&&monitor.modeCount==1&&monitor.duplicates==1&&(modes[0].sources&CtaVic));
    ext=cta(3);check("cta_multiple_extensions",parse(ext).ok()&&monitor.duplicates==3);
    ext=cta();ext[128+4]=0x5f;seal(ext,128);check("cta_crossing_data_block",!parse(ext).ok()&&monitor.modeCount==0);
    ext=cta();ext[128+2]=128;seal(ext,128);check("cta_invalid_dtd_offset",!parse(ext).ok());
    ext=cta();ext[128+1]=4;seal(ext,128);check("cta_revision_unsupported",!parse(ext).ok());
    ext=cta();ext[128]=0x70;seal(ext,128);check("displayid_default_refused",!parse(ext).ok());
    check("displayid_known_only_partial",parse(ext,ExtensionPolicy::KnownBlocksOnly).ok()&&monitor.partial&&!modes[0].hardwareVerified);
    ext=cta();ext[255]^=1;check("cta_checksum_reject",!parse(ext).ok());
    ext=cta();ext[130]=0;seal(ext,128);check("cta_zero_offset_cannot_hide_data",!parse(ext).ok());
    ext=cta();const uint8_t hdmiBlocks[]={0x67,3,12,0,0,0,0,30,0x67,0xd8,0x5d,0xc4,1,120,0x80,0};
    for(unsigned i=0;i<sizeof(hdmiBlocks);++i)ext[128+6+i]=hdmiBlocks[i];
    ext[130]=22;seal(ext,128);
    check("cta_hdmi_advertisement",parse(ext).ok()&&monitor.scdcAdvertised&&monitor.sinkMaxTmdsKHz==600000&&!modes[0].hardwareVerified);
    ext[128+14]=0x66;ext[130]=21;seal(ext,128);check("cta_short_forum_block",!parse(ext).ok());
    check("mode_storage_budget",!NaviDisplay::edid({data.data(),128},Origin::Synthetic,monitor,modes,0).ok());
    data=M8Fixture::edid();data[35]=0x20;seal(data);check("mode_capacity_not_truncated",!NaviDisplay::edid({data.data(),128},Origin::Synthetic,monitor,modes,1).ok()&&monitor.modeCount==0);
    Edid::DetailedTiming t{148500,1920,280,88,44,1080,45,4,5,true,true,false};Mode mode{};
    check("timing_exact_fraction",timing(t,mode).ok()&&mode.refresh.numerator==60&&mode.refresh.denominator==1);
    t.hBlank=40;check("timing_geometry_refused",!timing(t,mode).ok());t.hBlank=280;t.pixelClockKHz=UINT32_MAX;
    check("timing_clock_budget",!timing(t,mode).ok());t.pixelClockKHz=148500;timing(t,mode);
    Decision decision{};LinkBudget unknown{};EngineBudget engine{};
    check("unknown_link_remains_unknown",assess(mode,unknown,engine,24,decision).ok()&&decision.link==Fit::Unknown&&!decision.outputAllowed);
    LinkBudget dp{Origin::Synthetic,LinkKind::Dp8b10b,4,2700,0};
    check("dp_budget_math",assess(mode,dp,engine,24,decision).ok()&&decision.linkPayloadBitsPerSecond==8640000000ULL&&decision.requiredBitsPerSecond==3564000000ULL&&decision.link==Fit::WithinBudget);
    check("frame_math",decision.frameBytes==8294400&&decision.fullFrameBytesPerSecond==497664000);
    dp.lanes=1;dp.rateMbps=1620;check("dp_insufficient",assess(mode,dp,engine,24,decision).ok()&&decision.link==Fit::Insufficient);
    dp.lanes=3;check("dp_bad_lanes",!assess(mode,dp,engine,24,decision).ok());dp.lanes=4;dp.rateMbps=2700;
    mode.hardwareVerified=true;check("mode_cannot_claim_hardware",!assess(mode,dp,engine,24,decision).ok());mode.hardwareVerified=false;
    mode.refresh.numerator=61;check("mode_fraction_tamper",!assess(mode,dp,engine,24,decision).ok());timing(t,mode);
    LinkBudget hdmi{Origin::Synthetic,LinkKind::Tmds,0,0,148500};
    check("tmds_rgb_8bpc",assess(mode,hdmi,engine,24,decision).ok()&&decision.link==Fit::WithinBudget);
    check("tmds_deep_color_budget",assess(mode,hdmi,engine,30,decision).ok()&&decision.link==Fit::Insufficient);
    engine={Origin::Synthetic,100000};check("engine_limit_independent",assess(mode,hdmi,engine,24,decision).ok()&&decision.engine==Fit::Insufficient&&!decision.outputAllowed);
    Edid::DetailedTiming high{734400,2560,160,48,32,1440,60,3,5,true,true,false};Mode highMode{};
    check("synthetic_1440p180_math",timing(high,highMode).ok()&&highMode.refresh.numerator==180&&highMode.refresh.denominator==1&&
        assess(highMode,unknown,EngineBudget{},24,decision).ok()&&decision.frameBytes==14745600&&
        decision.fullFrameBytesPerSecond==2654208000ULL&&!decision.outputAllowed);
    check("timing_alias_safe",timing(highMode.timing,highMode).ok()&&highMode.refresh.numerator==180);
    check("classic_dtd_clock_limit_below_180",uint64_t(655350000)<uint64_t(2560)*1440*180);
    Edid::DetailedTiming hostile{2500000,49998,1,0,1,49998,1,0,1,true,true,false};Mode huge{};
    check("frame_product_overflow_rejected",timing(hostile,huge).ok()&&!assess(huge,unknown,EngineBudget{},24,decision).ok()&&!decision.frameBytes);
    auto romData=rom();AtomBios atom;check("rom_valid",atom.init(romData.data(),romData.size())&&atom.imageLength()==1024);
    AtomBios::DisplayPath oversized[9]{};check("connector_storage_budget",atom.getDisplayPaths(oversized,9)==0);
    check("master_indices",AtomBios::DceInfo==27&&AtomBios::VramInfo==28&&AtomBios::VoltageObjectInfo==32);
    ConnectorList list{};auto board=[&](const auto&b){return connectors({b.data(),b.size()},Origin::Synthetic,list);};
    check("connectors_dp_hdmi",board(romData).ok()&&list.count==2&&list.entries[0].type==AtomBios::ConnectorDP&&list.entries[1].type==AtomBios::ConnectorHDMIA);
    check("connector_static_not_hardware",!list.boardVerified&&!list.entries[0].hardwareVerified&&!list.entries[0].routingKnown&&list.entries[0].records.hasI2c&&list.entries[0].records.hasHpd);
    romData[0]=0;seal(romData,0,1024);check("rom_signature_refused",!board(romData).ok()&&list.count==0);romData=rom();
    romData[100]^=1;check("rom_checksum_refused",!board(romData).ok());romData=rom();
    w16(romData,0x48,1023);seal(romData,0,1024);check("rom_header_outside_image",!board(romData).ok());romData=rom();
    romData[0x83]=9;seal(romData,0,1024);check("rom_header_version_refused",!board(romData).ok());romData=rom();
    romData[0x103]=9;seal(romData,0,1024);check("master_version_refused",!board(romData).ok());romData=rom();
    w16(romData,0x104+22*2,0x100);seal(romData,0,1024);check("master_cycle_refused",!board(romData).ok());romData=rom();
    w16(romData,0x104+21*2,0x180);seal(romData,0,1024);check("data_table_overlap_refused",!board(romData).ok());romData=rom();
    romData[0x183]=4;seal(romData,0,1024);check("display_v14_not_mixed",!board(romData).ok());romData=rom();
    romData[0x186]=9;seal(romData,0,1024);check("path_count_refused",!board(romData).ok());romData=rom();
    w16(romData,0x198,0x3113);seal(romData,0,1024);check("duplicate_connector_refused",!board(romData).ok());romData=rom();
    w16(romData,0x18a,8);seal(romData,0,1024);check("record_pointer_into_paths",!board(romData).ok());romData=rom();
    romData[0x180+41]=0;seal(romData,0,1024);check("zero_record_progress",!board(romData).ok());romData=rom();
    romData[0x180+44]=1;seal(romData,0,1024);check("duplicate_i2c_refused",!board(romData).ok());romData=rom();
    romData[0x180+58]=3;romData[0x180+59]=2;seal(romData,0,1024);
    check("record_chain_unterminated",!board(romData).ok()&&list.count==0);romData=rom();
    bool romTruncations=true;for(size_t n=0;n<1024;++n)romTruncations&=!connectors({romData.data(),n},Origin::Synthetic,list).ok();
    check("rom_all_truncations",romTruncations);
    romData[2]=1;seal(romData,0,512);w16(romData,0x104+22*2,0x300);seal(romData,0,512);
    check("rom_bounds_not_outer_blob",!board(romData).ok());
    atom.init(romData.data(),romData.size());check("rom_failure_clears_state",!atom.isValid()&&atom.imageLength()==0&&atom.subsystemId()==0);
    AtomBios::TableHeader th{999,1,1};check("invalid_table_index",atom.dataTable(static_cast<AtomBios::DataTable>(UINT32_MAX),&th)==0&&th.size==0);
    NaviHost::PlatformMock mock;uint8_t invalid[8]{};mock.snapshot={invalid,8};
    auto contract=mock.contract();auto r=NaviPlatform::validateSnapshot(contract,Asic::Target::Gfx1200);
    check("platform_release_on_parser_failure",!r.ok()&&mock.borrows==1&&mock.returns==1&&mock.allocations==1&&mock.releases==1&&mock.enters==mock.leaves&&!mock.inCall);
    mock.deny=true;r=NaviPlatform::validateSnapshot(contract,Asic::Target::Gfx1200);
    check("platform_input_release_on_no_scratch",r.code==Error::Budget&&mock.borrows==2&&mock.returns==2);
    mock.wrongContext=true;r=NaviPlatform::validateSnapshot(contract,Asic::Target::Gfx1200);
    check("platform_context_rejected",r.code==Error::Protocol&&mock.borrows==2&&mock.logs==2);
    mock.wrongContext=false;mock.inCall=true;r=NaviPlatform::validateSnapshot(contract,Asic::Target::Gfx1200);
    check("platform_reentry_rejected",r.code==Error::Protocol&&mock.borrows==2&&mock.logs==2);mock.inCall=false;
    contract.snapshots.release=nullptr;r=NaviPlatform::validateSnapshot(contract,Asic::Target::Gfx1200);
    check("platform_missing_lifetime_rejected",!r.ok()&&mock.borrows==2&&!mock.inCall);
    struct LogReentry {NaviPlatform::Contract c;unsigned calls{0};Result nested{success()};} hook{mock.contract()};
    hook.c.log={&hook,[](void*ctx,Result){
        auto&h=*static_cast<LogReentry*>(ctx);++h.calls;
        // Bound the test even on broken implementations; a second log is FAIL.
        if(h.calls>1)return;
        h.nested=NaviPlatform::validateSnapshot(h.c,Asic::Target::Gfx1200);
    }};
    NaviPlatform::validateSnapshot(hook.c,Asic::Target::Gfx1200);
    check("platform_log_reentry_no_recursion",hook.calls==1&&hook.nested.code==Error::Protocol&&!mock.inCall);
    const uint8_t text[]={'1','2','3','4','5','6','7','8','9'};Integrity integrity{};
    check("crc32_known_vector",payloadChecksum({text,9},0xcbf43926,CrcConvention::IsoHdlc,integrity).ok()&&integrity.checksumMatched&&!integrity.signatureVerified&&!integrity.loadable);
    check("crc32_corruption",!payloadChecksum({text,8},0xcbf43926,CrcConvention::IsoHdlc,integrity).ok()&&!integrity.checksumMatched);
    check("crc32_unknown_convention",!payloadChecksum({text,9},0xcbf43926,CrcConvention::Unknown,integrity).ok());
    check("crc32_empty_vector",payloadChecksum({nullptr,0},0,CrcConvention::IsoHdlc,integrity).ok());
    QueryCandidate query{};query.device.profile=Asic::identify(0x1002,0x7590);query.provenance=Provenance::Synthetic;query.generation=1;
    uint8_t wire[128]{};QueryCandidate decoded{};
    check("query_envelope_roundtrip",encodeQuery(query,wire,128).ok()&&decodeQuery({wire,128},decoded).ok()&&decoded.device.profile.target==Asic::Target::Gfx1200&&decoded.provenance==Provenance::Synthetic);
    wire[13]=1;check("query_false_verification_rejected",!decodeQuery({wire,128},decoded).ok()&&!decoded.generation);wire[13]=0;
    wire[14]=1;check("query_false_owner_rejected",!decodeQuery({wire,128},decoded).ok());wire[14]=0;
    wire[6]=1;check("query_unknown_minor_rejected",!decodeQuery({wire,128},decoded).ok());wire[6]=0;
    wire[12]=3;check("query_no_hardware_provenance",!decodeQuery({wire,128},decoded).ok());wire[12]=1;
    wire[16]=1;check("query_presence_mismatch",!decodeQuery({wire,128},decoded).ok());wire[16]=0;
    wire[20]=1;check("query_false_capabilities",!decodeQuery({wire,128},decoded).ok());wire[20]=0;
    OfflineOwner owner;check("offline_owner_prepare",owner.prepare(query).ok()&&!owner.canInitializeHardware());
    check("offline_owner_lease",owner.borrow(decoded).ok()&&decoded.generation==1);
    check("offline_owner_reentry",!owner.borrow(decoded).ok());
    check("offline_owner_return",owner.giveBack(1).ok());owner.close();
    check("offline_owner_after_close",!owner.borrow(decoded).ok()&&!decoded.generation);
    check("offline_owner_generation_replay",!owner.prepare(query).ok());query.generation=2;
    check("offline_owner_next_generation",owner.prepare(query).ok()&&owner.borrow(decoded).ok());
    check("offline_owner_wrong_epoch_terminal",!owner.giveBack(1).ok()&&!owner.borrow(decoded).ok());
    query.generation=3;check("offline_owner_failure_not_promoted",!owner.prepare(query).ok());
    std::array<uint8_t,64> elfbytes{};const uint8_t ident[]={0x7f,'E','L','F',2,1,1};
    for(unsigned i=0;i<7;++i)elfbytes[i]=ident[i];
    w16(elfbytes,16,3);w16(elfbytes,18,224);elfbytes[20]=1;elfbytes[48]=72;
    w16(elfbytes,52,64);w16(elfbytes,54,56);w16(elfbytes,56,5000);w16(elfbytes,58,64);w16(elfbytes,60,2);
    Node arena[2]{};Scratch scratch{arena,2,0};
    check("elf_table_count_budget",elf({elfbytes.data(),64},Asic::Target::Gfx1200,scratch).code==Error::Budget);
    std::vector<uint8_t> boundedLarge((16u<<20)+1);
    check("elf_direct_input_budget",elf({boundedLarge.data(),boundedLarge.size()},Asic::Target::Gfx1200,scratch).code==Error::Budget);
    auto didExt=displayId1440p180();
    check("displayid_policy_default_refused",!parse(didExt,ExtensionPolicy::RejectUnknown).ok());
    check("displayid_1440p180_parsed",parse(didExt,ExtensionPolicy::AllowDisplayId).ok()&&monitor.modeCount==2&&
        modes[1].timing.hActive==2560&&modes[1].timing.vActive==1440&&
        modes[1].timing.pixelClockKHz==734400&&modes[1].refresh.numerator==180&&modes[1].refresh.denominator==1&&
        (modes[1].sources&DisplayIdType1)&&!modes[1].hardwareVerified);
    LinkBudget dpHbr3{Origin::Synthetic,LinkKind::Dp8b10b,4,8100,0};
    check("displayid_1440p180_dp_hbr3_budget",assess(modes[1],dpHbr3,EngineBudget{Origin::Synthetic,900000},24,decision).ok()&&
        decision.link==Fit::WithinBudget&&decision.engine==Fit::WithinBudget&&!decision.outputAllowed);
    auto didBadSum=displayId1440p180();didBadSum[128+28]^=1;seal(didBadSum,128);
    check("displayid_section_checksum_reject",!parse(didBadSum,ExtensionPolicy::AllowDisplayId).ok());
    auto didStereo=displayId1440p180();didStereo[128+8+3]|=0x20;
    {uint8_t s=0;didStereo[128+28]=0;for(size_t i=129;i<128+28;++i)s=uint8_t(s+didStereo[i]);didStereo[128+28]=uint8_t(0-s);seal(didStereo,128);}
    check("displayid_stereo_rejected",!parse(didStereo,ExtensionPolicy::AllowDisplayId).ok());
    auto didTrailing=displayId1440p180();didTrailing[128+40]=1;seal(didTrailing,128);
    check("displayid_nonzero_padding_rejected",!parse(didTrailing,ExtensionPolicy::AllowDisplayId).ok());
    auto didV12=displayIdV12Tag03_1440p180();
    check("displayid_v12_tag03_1440p180_parsed",parse(didV12,ExtensionPolicy::AllowDisplayId).ok()&&monitor.modeCount==2&&
        modes[1].timing.hActive==2560&&modes[1].timing.vActive==1440&&
        modes[1].timing.pixelClockKHz==725100&&(modes[1].sources&DisplayIdType1));
    BoardDiagnostics bdiag{};romData=rom();
    check("board_diagnostics_synthetic_rom",boardDiagnostics({romData.data(),romData.size()},Origin::Synthetic,bdiag).ok()&&
        bdiag.origin==Origin::Synthetic&&!bdiag.hardwareVerified);
    QueryCandidate qProj{};
    qProj.device.profile=Asic::identify(0x1002,0x7590,0xc0,true);
    qProj.device.present=7u;
    qProj.device.gcMajor=12;qProj.device.gcMinor=0;qProj.device.gcRevision=0;
    qProj.device.se=2;qProj.device.cu=32;qProj.device.rb=8;qProj.device.tcc=8;qProj.device.gbAddrConfig=0x00000243u;
    qProj.device.vramBytes=16ULL<<30;qProj.device.visibleBarBytes=16ULL<<30;
    qProj.provenance=Provenance::StaticReference;qProj.generation=42;
    CobaltQueryProjection proj{},projDecoded{};uint8_t wire192[192]{};
    check("cobalt_projection_encode_decode",projectToCobaltInfo(qProj,proj,wire192,192).ok()&&
        decodeCobaltProjection({wire192,192},projDecoded).ok()&&
        projDecoded.vendorId==0x1002&&projDecoded.deviceId==0x7590&&projDecoded.revisionId==0xc0&&
        projDecoded.gcVersion==((12u<<16)|(0u<<8)|0u)&&projDecoded.gbAddrConfig==0x00000243u&&
        projDecoded.vramVisTotal==(16ULL<<30)&&projDecoded.vramVisFree==0&&projDecoded.flags==0&&
        projDecoded.generation==42);
    wire192[8]=4; // Attempt to forge N48N_INFO_NATIVE_BOOT
    check("cobalt_projection_forged_boot_flag_rejected",!decodeCobaltProjection({wire192,192},projDecoded).ok());
    wire192[8]=0;wire192[40]=1; // Attempt to forge non-zero free VRAM pool offline
    check("cobalt_projection_forged_free_pool_rejected",!decodeCobaltProjection({wire192,192},projDecoded).ok());
    wire192[40]=0;wire192[168]=0x4e; // Attempt to forge gfx1201 target on 0x7590
    check("cobalt_projection_target_mismatch_rejected",!decodeCobaltProjection({wire192,192},projDecoded).ok());
    std::cout<<"SUMMARY "<<pass<<' '<<fail<<'\n';return fail?1:0;
}
