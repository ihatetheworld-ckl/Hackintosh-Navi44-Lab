#include "lifecycle.hpp"
namespace NaviPlatform {
using namespace NaviCore;
namespace { Result context(){return failure("lifetime_context_or_reentry",Error::Protocol);} }
bool SnapshotOwner::held()const{
    return access_.execution.enter&&access_.execution.leave&&access_.isHeld&&
        access_.isHeld(access_.execution.context);
}
SnapshotOwner::Call::Call(SnapshotOwner&o):owner(o),entered(o.held()&&!o.operation_){
    if(entered)o.operation_=true;
}
SnapshotOwner::Call::~Call(){if(entered)owner.operation_=false;}
bool SnapshotOwner::valid(const SnapshotTicket&t)const{
    return t.identity==this&&t.owner==generation_&&t.serial&&t.slot<MaxLeases&&slots_[t.slot]==t.serial;
}
Result SnapshotOwner::finish(){
    if(leases_)return failure("snapshot_shutdown_pending",Error::Protocol);
    if(prepared_){
        Result r=reference_.complete(reference_.context);
        if(!r.ok()){state_=OwnerState::Failed;return r;}
        prepared_=false;
    }
    input_={};state_=OwnerState::Released;
    if(retained_){retained_=false;reference_.release(reference_.context);}
    reference_={};return success();
}
Result SnapshotOwner::fail(Result error){
    input_={};Result cleanup=finish();state_=OwnerState::Failed;
    return cleanup.ok()?error:cleanup;
}
Result SnapshotOwner::activate(ReferenceOps ref,bool needsPreparation){
    Call call{*this};if(!call.entered)return context();
    if(state_!=OwnerState::Created)return failure("snapshot_activation_state",Error::Protocol);
    if(!generation_||!ref.retain||!ref.release||!ref.view||
       (needsPreparation&&(!ref.prepare||!ref.complete))){
        state_=OwnerState::Failed;return failure("snapshot_reference_contract",Error::Protocol);
    }
    reference_=ref;
    if(!reference_.retain(reference_.context)){state_=OwnerState::Failed;reference_={};return failure("snapshot_retain_failed",Error::Budget);}
    retained_=true;
    Result r=reference_.view(reference_.context,input_);if(!r.ok())return fail(r);
    const uintptr_t address=reinterpret_cast<uintptr_t>(input_.data);
    if(!input_.data||!input_.size||input_.size>MaxBytes||input_.size-1>UINTPTR_MAX-address)
        return fail(failure("snapshot_view_bounds",Error::Bounds));
    if(needsPreparation){r=reference_.prepare(reference_.context);if(!r.ok())return fail(r);prepared_=true;}
    state_=OwnerState::Active;return success();
}
Result SnapshotOwner::borrowHeld(SnapshotTicket&out){
    out={};if(state_!=OwnerState::Active)return failure("snapshot_not_active",Error::Protocol);
    if(leases_==MaxLeases||next_==UINT64_MAX)return failure("snapshot_lease_budget",Error::Budget);
    size_t i=0;while(i<MaxLeases&&slots_[i])++i;
    if(i==MaxLeases)return failure("snapshot_slot_state",Error::Protocol);
    slots_[i]=next_++;++leases_;out={generation_,slots_[i],i,this};return success();
}
Result SnapshotOwner::borrow(SnapshotTicket&out){
    // Do not overwrite an existing obligation to return a live ticket.
    if(out.owner||out.serial||out.identity)return failure("snapshot_ticket_output_occupied",Error::Protocol);
    out={};Call call{*this};return call.entered?borrowHeld(out):context();
}
Result SnapshotOwner::readHeld(const SnapshotTicket&t,View&out)const{
    out={};if(!valid(t))return failure("snapshot_ticket_invalid",Error::Protocol);
    if(state_!=OwnerState::Active)return failure("snapshot_revoked_or_closing",Error::Protocol);
    out=input_;return success();
}
Result SnapshotOwner::read(const SnapshotTicket&t,View&out){
    out={};Call call{*this};return call.entered?readHeld(t,out):context();
}
Result SnapshotOwner::returnHeld(SnapshotTicket&t){
    if(!valid(t))return failure("snapshot_ticket_invalid",Error::Protocol);
    slots_[t.slot]=0;--leases_;t={};
    if(state_!=OwnerState::Active&&leases_==0)return finish();
    return success();
}
Result SnapshotOwner::giveBack(SnapshotTicket&t){
    Call call{*this};return call.entered?returnHeld(t):context();
}
Result SnapshotOwner::stop(OwnerState state){
    Call call{*this};if(!call.entered)return context();
    if(state_==OwnerState::Released)return success();
    if(state_==OwnerState::Active||state_==OwnerState::Created)state_=state;
    // Close may follow revoke/failed completion; retry cleanup without reopening.
    input_={};return finish();
}
Result SnapshotOwner::close(){return stop(OwnerState::Closing);}
Result SnapshotOwner::revoke(){return stop(OwnerState::Revoked);}
bool SnapshotOwner::readyToFree()const{
    return held()&&!operation_&&state_==OwnerState::Released&&!leases_&&!retained_&&!prepared_;
}
Result SnapshotOwner::inspect(OwnerState&state,size_t&count)const{
    state=OwnerState::Failed;count=0;if(!held()||operation_)return context();
    state=state_;count=leases_;return success();
}
Result SnapshotOwner::legacyBorrow(void*ctx,SnapshotKind kind,View&out){
    auto&o=*static_cast<SnapshotOwner*>(ctx);out={};Call call{o};if(!call.entered)return context();
    if(kind!=o.kind_||o.legacy_)return failure("snapshot_legacy_borrow",Error::Protocol);
    Result r=o.borrowHeld(o.legacyTicket_);if(!r.ok())return r;
    r=o.readHeld(o.legacyTicket_,out);
    if(!r.ok()){o.returnHeld(o.legacyTicket_);return r;}
    o.legacy_=true;o.legacyView_=out;return success();
}
void SnapshotOwner::legacyRelease(void*ctx,View input){
    auto&o=*static_cast<SnapshotOwner*>(ctx);Call call{o};if(!call.entered)return;
    if(!o.legacy_||input.data!=o.legacyView_.data||input.size!=o.legacyView_.size)return;
    o.legacy_=false;o.legacyView_={};o.returnHeld(o.legacyTicket_);
}
}
