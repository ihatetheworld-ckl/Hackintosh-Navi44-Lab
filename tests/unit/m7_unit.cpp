// New M7 CPU behavior tests; no GPU/OS/kernel calls. BSD-3-Clause.
#include "../../development/AMDRadeonRDNA4-Navi44/core/validation.hpp"
#include "../../development/AMDRadeonRDNA4-Navi44/core/device_info.hpp"
#include "../../development/AMDRadeonRDNA4-Navi44/core/model.hpp"
#include "../../development/AMDRadeonRDNA4-Navi44/platform/darwin_contract.hpp"
#include "../../development/AMDRadeonRDNA4-Navi44/host/platform_mock.hpp"
#include <iostream>
#include <type_traits>
int main(){
    unsigned pass=0,fail=0;auto check=[&](const char*n,bool ok){std::cout<<(ok?"PASS ":"FAIL ")<<n<<'\n';ok?++pass:++fail;};
    using namespace NaviCore;
    uint8_t bytes[8]{};View view{bytes,sizeof(bytes)},out{nullptr,0};
    check("view_full",view.slice(0,8,out).ok()&&out.data==bytes&&out.size==8);
    check("view_empty_boundary",view.slice(8,0,out).ok()&&!out.data&&out.size==0);
    check("view_overflow",!view.slice(UINT64_MAX,4,out).ok()&&out.size==0);
    check("view_null_length",!View{nullptr,8}.inside(0,1));
    check("error_fixed_width",sizeof(Error)==1&&std::is_standard_layout<View>::value);
    check("core_never_authorizes_hardware",!hardwareAllowed());
    Session state;check("core_failed_state_terminal",!state.advance(State::OfflineReady)&&state.state==State::Failed&&!state.advance(State::PciMatched));
    IpDiscovery absent;FirmwareRequirement needs[16]{};needs[0].component="stale";size_t count=8;
    check("core_manifest_failure_clears",!firmwareRequirements(Asic::identify(0x1002,0x7590),absent,needs,count).ok()&&!count&&!needs[0].component);
    NaviHost::PlatformMock mock;
    {NaviPlatform::Lease lease(mock.contract().memory);check("lease_allocate",lease.open(32,8));
     check("lease_view",lease.view().size==32);check("lease_reopen_reject",!lease.open(32,8));
     lease.close();check("lease_view_invalidated",!lease.view().data&&!lease.view().size);lease.close();}
    check("lease_single_release",mock.allocations==1&&mock.releases==1&&!mock.busy);
    check("no_snapshot_no_allocation",!NaviPlatform::validateSnapshot(mock.contract(),Asic::Target::Gfx1200).ok()&&mock.allocations==1);
    mock.snapshot={bytes,sizeof(bytes)};
    auto r=NaviPlatform::validateSnapshot(mock.contract(),Asic::Target::Gfx1200);
    check("parser_failure_releases",!r.ok()&&mock.allocations==2&&mock.releases==2);
    mock.deny=true;r=NaviPlatform::validateSnapshot(mock.contract(),Asic::Target::Gfx1200);
    check("allocation_failure_explicit",r.code==Error::Budget&&mock.allocations==2);
    check("mock_logs",mock.logs==3);
    NaviDarwin::AdapterDraft draft{mock.contract(),false};check("darwin_draft_no_hardware",!draft.appleSdkValidated&&!draft.hardwareInitializationAllowed());
    Node nodes[2]{};Scratch scratch{nodes,2,1};r=elf({bytes,8},Asic::Target::Gfx1200,scratch);
    check("failure_scratch_reset",!r.ok()&&scratch.used==0);
    uint8_t wire[96]{};DeviceInfo info{};info.profile=Asic::identify(0x1002,0x7590);
    check("abi_v2_unknown_roundtrip",encodeDeviceInfo(info,wire,sizeof(wire)).ok());
    DeviceInfo decoded{};check("abi_v2_decode",decodeDeviceInfo({wire,96},decoded).ok()&&decoded.profile.target==Asic::Target::Gfx1200&&decoded.present==0);
    wire[20]=1;check("abi_v2_capabilities_rejected",!decodeDeviceInfo({wire,96},decoded).ok()&&decoded.present==0);wire[20]=0;
    wire[80]=1;check("abi_v2_reserved_rejected",!decodeDeviceInfo({wire,96},decoded).ok());wire[80]=0;
    info.present=1;info.gcMajor=12;check("abi_v2_gc",encodeDeviceInfo(info,wire,96).ok());
    info.gcRevision=1;check("abi_v2_gc_mismatch",!encodeDeviceInfo(info,wire,96).ok());info.gcRevision=0;
    info.present=0;check("abi_v2_unknown_gc_rejected",!encodeDeviceInfo(info,wire,96).ok());info.gcMajor=0;
    info.profile.revisionVerified=true;check("abi_v2_fake_verified_rejected",!encodeDeviceInfo(info,wire,96).ok());info.profile.revisionVerified=false;
    info.present=4;info.vramBytes=1024;info.visibleBarBytes=2048;check("abi_v2_bar_range",!encodeDeviceInfo(info,wire,96).ok());
    info.visibleBarBytes=512;check("abi_v2_memory_present_not_capable",encodeDeviceInfo(info,wire,96).ok()&&decodeDeviceInfo({wire,96},decoded).ok()&&decoded.profile.capabilities==0&&!decoded.profile.topology.verified);
    info.profile=Asic::identify(0x1002,0x7550);info.present=1;info.gcMajor=12;info.gcRevision=1;info.vramBytes=info.visibleBarBytes=0;
    check("abi_v2_navi48",encodeDeviceInfo(info,wire,96).ok());
    Package package{};r=pspPackage({bytes,8},package);check("package_failure_zeroed",!r.ok()&&package.count==0&&!package.signatureVerified);
    std::cout<<"SUMMARY "<<pass<<' '<<fail<<'\n';return fail?1:0;
}
