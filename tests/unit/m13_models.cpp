// CPU-only models and length-output alias regression. BSD-3-Clause.
#include "../../development/AMDRadeonRDNA4-Navi44/core/driver_model.hpp"
#include "../../development/AMDRadeonRDNA4-Navi44/core/displayid.hpp"
#include "../../development/AMDRadeonRDNA4-Navi44/platform/resource_model.hpp"
#include "../../development/AMDRadeonRDNA4-Navi44/host/lifecycle_mock.hpp"
#include <array>
#include <iostream>
#include <new>
using namespace NaviCore;using namespace NaviModel;using namespace NaviPlatform;using namespace NaviHost;
using Bytes=std::array<uint8_t,128>;
static void outer(Bytes&b){unsigned sum=0;b[127]=0;for(unsigned i=0;i<127;++i)sum+=b[i];b[127]=static_cast<uint8_t>(0-sum);}
static void checksums(Bytes&b){const unsigned end=5+b[2];b[end]=0;unsigned sum=0;for(unsigned i=1;i<end;++i)sum+=b[i];b[end]=static_cast<uint8_t>(0-sum);outer(b);}
int main(){unsigned pass=0,fail=0;auto check=[&](const char*n,bool ok){std::cout<<(ok?"PASS ":"FAIL ")<<n<<'\n';ok?++pass:++fail;};
    {
        Bytes b{};b[0]=0x70;b[1]=0x20;b[2]=4;b[3]=5;b[5]=0x22;b[7]=1;b[8]=17;checksums(b);
        NaviDisplay::DisplayIdSection out{};
        check("displayid_opaque_block_inventory",NaviDisplay::displayIdSection({b.data(),128},out).ok()&&out.count==1&&out.blocks[0].bytes==1&&!out.timingDecoded&&!out.outputAllowed);
        auto bad=b;bad[127]^=1;check("displayid_outer_checksum",!NaviDisplay::displayIdSection({bad.data(),128},out).ok()&&!out.count);
        bad=b;bad[8]^=1;outer(bad);check("displayid_inner_checksum",!NaviDisplay::displayIdSection({bad.data(),128},out).ok());
        bad=b;bad[2]=255;outer(bad);check("displayid_length_overflow",!NaviDisplay::displayIdSection({bad.data(),128},out).ok());
        bad=b;bad[7]=2;checksums(bad);check("displayid_block_overrun",!NaviDisplay::displayIdSection({bad.data(),128},out).ok());
        bad=b;bad[4]=1;checksums(bad);check("displayid_continuation_unsupported",!NaviDisplay::displayIdSection({bad.data(),128},out).ok());
        bad=b;bad[1]=0x21;checksums(bad);check("displayid_unknown_version",!NaviDisplay::displayIdSection({bad.data(),128},out).ok());
        bad=b;bad[30]=1;checksums(bad);check("displayid_nonzero_padding",!NaviDisplay::displayIdSection({bad.data(),128},out).ok());
        check("displayid_truncated",!NaviDisplay::displayIdSection({b.data(),127},out).ok());
        bad=b;bad[1]=0x13;checksums(bad);check("displayid_v13_container",NaviDisplay::displayIdSection({bad.data(),128},out).ok()&&!out.hardwareVerified);
        bad=b;bad[2]=2;checksums(bad);check("displayid_truncated_block_header",!NaviDisplay::displayIdSection({bad.data(),128},out).ok());
        uint32_t seed=759013;bool invariant=true;unsigned accepted=0;
        for(unsigned i=0;i<500;++i){bad=b;seed=seed*1664525u+1013904223u;bad[(seed>>8)%128]^=static_cast<uint8_t>((seed>>24)|1);auto r=NaviDisplay::displayIdSection({bad.data(),128},out);
            if(r.ok()){++accepted;invariant=invariant&&out.count<=32&&!out.timingDecoded&&!out.outputAllowed;}else invariant=invariant&&!out.count;}
        check("displayid_500_fixed_mutations",invariant);std::cout<<"M13_DISPLAYID seed=759013 inputs=500 accepted="<<accepted<<'\n';
    }
    {
        QueryCandidate q{};q.device.profile=Asic::identify(0x1002,0x7590);q.provenance=Provenance::Synthetic;q.generation=1;DevicePlan p{};
        check("navi44_candidate_no_runtime_capability",planDevice(q,p).ok()&&p.target==Asic::Target::Gfx1200&&p.backend==Readiness::Unverified&&!p.hardwareAllowed&&!p.displayAllowed&&!p.shaderAllowed);
        q.device.profile=Asic::identify(0x1002,0x7550);check("navi48_not_reused_as_navi44",!planDevice(q,p).ok()&&!p.hardwareAllowed);
        q.device.profile=Asic::identify(0x1002,0x7590);q.device.profile.capabilities=1;check("unverified_capability_injection",!planDevice(q,p).ok());
        NaviDisplay::Mode mode{};Edid::DetailedTiming t{724608,2560,160,16,32,1440,40,1,5,true,true,false};
        check("synthetic_1440p180_timing",NaviDisplay::timing(t,mode).ok()&&mode.refresh.numerator==180&&mode.refresh.denominator==1);
        NaviDisplay::Connector c{};c.type=AtomBios::ConnectorDP;NaviDisplay::LinkBudget link{NaviDisplay::Origin::Synthetic,NaviDisplay::LinkKind::Dp8b10b,4,8100,0};NaviDisplay::EngineBudget engine{NaviDisplay::Origin::Synthetic,800000};DisplayPlan plan{};
        check("synthetic_budget_is_not_scanout",planDisplay(mode,c,link,engine,24,plan).ok()&&plan.arithmetic.link==NaviDisplay::Fit::WithinBudget&&!plan.scanoutAllowed&&!plan.trainingAllowed&&plan.routing==Readiness::Unverified);
        link.lanes=1;check("insufficient_display_link",planDisplay(mode,c,link,engine,24,plan).ok()&&plan.arithmetic.link==NaviDisplay::Fit::Insufficient&&!plan.scanoutAllowed);
        link={};check("missing_display_link",planDisplay(mode,c,link,engine,24,plan).ok()&&plan.arithmetic.link==NaviDisplay::Fit::Unknown);
        c.type=AtomBios::ConnectorUnknown;check("unknown_connector",!planDisplay(mode,c,link,engine,24,plan).ok());
        c.type=static_cast<AtomBios::ConnectorType>(255);check("unsupported_connector_encoding",!planDisplay(mode,c,link,engine,24,plan).ok());
        c.type=AtomBios::ConnectorDP;c.routingKnown=true;check("untrusted_routing_claim",!planDisplay(mode,c,link,engine,24,plan).ok());c.routingKnown=false;
        check("unsupported_pixel_encoding",!planDisplay(mode,c,link,engine,16,plan).ok());
        mode.timing.hSyncWidth=200;check("invalid_display_geometry",!planDisplay(mode,c,link,engine,24,plan).ok());
    }
    {
        ThreadGate gate;GenerationClock clock(gate.access());ResourceModel m(gate.access(),clock,0x10000,0x10000,0x8000),other(gate.access(),clock,0x10000,0x10000,0x8000);ModelHandle h{};
        check("resource_wrong_context",!m.reserve(0x10000,4096,h).ok());GateScope hold(gate.access());
        check("resource_valid_reservation",m.reserve(0x10000,4096,h).ok()&&!m.hardwareSubmissionAllowed());
        ModelHandle second{};check("resource_overlap_rejected",!m.reserve(0x10000,4096,second).ok());
        check("resource_alignment_rejected",!m.reserve(0x11001,4096,second).ok());
        check("resource_window_overrun",!m.reserve(0x1f000,8192,second).ok());
        check("resource_budget_rejected",!m.reserve(0x11000,0x8000,second).ok());
        ResourceInfo info{};check("resource_cross_owner_isolation",!other.inspect(h,info).ok());
        const auto live=h;check("resource_occupied_output_preserved",!m.reserve(0x12000,4096,h).ok()&&h.generation==live.generation);
        ModelFence f{};check("model_fence_queue",m.queueModel(h,10,20,f).ok());
        check("pending_fence_prevents_release",!m.release(h).ok()&&h.generation==live.generation);
        check("model_fence_complete",m.completeModel(f).ok());check("double_fence_complete_rejected",!m.completeModel(f).ok());
        const auto old=f;f={};check("new_fence_generation",m.queueModel(h,20,30,f).ok()&&f.serial!=old.serial);check("stale_fence_rejected",!m.completeModel(old).ok());
        m.expireModel(29);m.inspect(h,info);check("timeout_not_premature",info.fence==FenceState::Pending);
        m.expireModel(30);m.inspect(h,info);check("timeout_poison",info.fence==FenceState::TimedOut&&info.revoked);
        check("timeout_is_not_quiescence",!m.release(h).ok()&&!m.completeModel(f).ok());
        check("timeout_cancel_acknowledgement",m.acknowledgeCancellationModel(f).ok()&&m.release(h).ok());
        check("stale_buffer_rejected",!m.inspect(live,info).ok());
        check("address_reuse_unique_generation",m.reserve(0x10000,4096,h).ok()&&h.generation!=live.generation);
        f={};m.queueModel(h,30,40,f);check("reset_revokes_without_early_free",m.resetModel().ok()&&!m.release(h).ok()&&!m.readyToFree());
        check("stopped_model_no_new_resources",!m.reserve(0x11000,4096,second).ok());
        check("reset_drain_then_free",m.acknowledgeCancellationModel(f).ok()&&m.release(h).ok()&&m.readyToFree());
        check("repeat_stop_no_double_free",m.stop().ok()&&m.readyToFree()&&!m.release(h).ok());
        ResourceModel overflow(gate.access(),clock,UINT64_MAX-4095,8192,8192);check("window_integer_overflow",!overflow.reserve(UINT64_MAX-4095,4096,second).ok());
        GenerationClock exhausted(gate.access(),UINT64_MAX);ResourceModel full(gate.access(),exhausted,0,65536,65536);check("generation_exhaustion_atomic",!full.reserve(0,4096,second).ok()&&!second.owner);
        ResourceModel slots(gate.access(),clock,0,65536,65536);ModelHandle handles[9]{};bool okay=true;
        for(unsigned i=0;i<8;++i)okay=slots.reserve(i*4096,4096,handles[i]).ok()&&okay;
        check("fixed_resource_capacity",okay&&!slots.reserve(8*4096,4096,handles[8]).ok());slots.stop();for(auto&handle:handles)if(handle.owner)slots.release(handle);
        check("capacity_failure_cleanup",slots.readyToFree());
    }
    {
        ThreadGate gate;GateScope hold(gate.access());ReferenceMock r;alignas(size_t) uint8_t storage[64]{};
        size_t*alias=new(storage+16)size_t(0x33003300);r.useOverride=true;r.overrideView={storage,sizeof(storage)};SnapshotOwner owner(gate.access(),99);owner.activate(r.ops());
        struct Context{size_t*p;bool rejected{false};} context{alias};
        auto callback=[](void*p,const ScopedInput&input)noexcept->Result{auto&c=*static_cast<Context*>(p);c.rejected=!input.length(*c.p).ok()&&*c.p==0x33003300;return success();};
        check("scope_length_output_alias_preserves_input",owner.consume({&context,callback}).ok()&&context.rejected);
        check("scope_length_alias_cleanup",owner.close().ok()&&owner.readyToFree()&&r.releases==1);
    }
    std::cout<<"SUMMARY "<<pass<<' '<<fail<<'\n';return fail?1:0;
}
