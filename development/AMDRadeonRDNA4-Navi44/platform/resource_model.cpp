#include "resource_model.hpp"
namespace NaviModel {
using namespace NaviCore;
bool ResourceModel::held()const{return access_.isHeld&&access_.execution.enter&&access_.execution.leave&&access_.isHeld(access_.execution.context);}
bool ResourceModel::valid(const ModelHandle&h)const{return h.owner==this&&h.generation&&h.slot<8&&entries_[h.slot].generation==h.generation;}
Result ResourceModel::reserve(uint64_t base,uint64_t bytes,ModelHandle&out){
    if(out.owner||out.generation)return failure("model_handle_occupied",Error::Protocol);
    out={};if(!held()||stopped_)return failure("model_closed_or_context",Error::Protocol);
    if(!bytes_||bytes_-1>UINT64_MAX-base_||!bytes||base%4096||bytes%4096||base<base_||base-base_>bytes_||bytes>bytes_-(base-base_))return failure("model_address_bounds",Error::Bounds);
    if(used_>budget_||bytes>budget_-used_)return failure("model_budget",Error::Budget);
    size_t slot=8;
    for(size_t i=0;i<8;++i){const auto&e=entries_[i];if(!e.generation){if(slot==8)slot=i;continue;}
        if(base<=e.base+e.bytes-1&&e.base<=base+bytes-1)return failure("model_overlap",Error::Bounds);}
    if(slot==8)return failure("model_slots",Error::Budget);
    uint64_t generation=0;Result r=clock_.issue(generation);if(!r.ok())return r;
    entries_[slot]={generation,base,bytes,0,0,FenceState::Idle,false};used_+=bytes;out={this,generation,slot};return success();
}
Result ResourceModel::queueModel(const ModelHandle&h,uint64_t now,uint64_t deadline,ModelFence&out){
    if(out.serial||out.buffer.owner||out.buffer.generation)return failure("model_fence_occupied",Error::Protocol);
    out={};if(!held()||stopped_||!valid(h))return failure("model_queue_context_or_handle",Error::Protocol);
    auto&e=entries_[h.slot];if(e.revoked||e.fence==FenceState::Pending||e.fence==FenceState::TimedOut||deadline<=now)return failure("model_fence_state",Error::Protocol);
    uint64_t serial=0;Result r=clock_.issue(serial);if(!r.ok())return r;
    e.serial=serial;e.deadline=deadline;e.fence=FenceState::Pending;out={h,serial};return success();
}
Result ResourceModel::completeModel(const ModelFence&f){
    if(!held()||!valid(f.buffer)||!f.serial)return failure("model_fence_invalid",Error::Protocol);
    auto&e=entries_[f.buffer.slot];if(e.revoked||e.serial!=f.serial||e.fence!=FenceState::Pending)return failure("model_fence_stale",Error::Protocol);
    e.fence=FenceState::Completed;return success();
}
Result ResourceModel::expireModel(uint64_t now){
    if(!held())return failure("model_context",Error::Protocol);
    for(auto&e:entries_)if(e.generation&&e.fence==FenceState::Pending&&now>=e.deadline){e.fence=FenceState::TimedOut;e.revoked=true;}
    return success();
}
Result ResourceModel::acknowledgeCancellationModel(const ModelFence&f){
    if(!held()||!valid(f.buffer)||!f.serial)return failure("model_cancel_invalid",Error::Protocol);
    auto&e=entries_[f.buffer.slot];
    if(!e.revoked||e.serial!=f.serial||(e.fence!=FenceState::Pending&&e.fence!=FenceState::TimedOut))return failure("model_cancel_state",Error::Protocol);
    e.fence=FenceState::Revoked;return success(); // CPU simulation acknowledgement, never hardware quiescence.
}
Result ResourceModel::inspect(const ModelHandle&h,ResourceInfo&out)const{
    out={};if(!held()||!valid(h))return failure("model_handle_invalid",Error::Protocol);
    const auto&e=entries_[h.slot];out={e.base,e.bytes,e.fence,e.revoked};return success();
}
Result ResourceModel::release(ModelHandle&h){
    if(!held()||!valid(h))return failure("model_release_invalid",Error::Protocol);
    auto&e=entries_[h.slot];if(e.fence==FenceState::Pending||e.fence==FenceState::TimedOut)return failure("model_pending_fence",Error::Protocol);
    used_-=e.bytes;e={};h={};return success();
}
Result ResourceModel::stop(){
    if(!held())return failure("model_context",Error::Protocol);stopped_=true;
    for(auto&e:entries_)if(e.generation)e.revoked=true;
    return success();
}
Result ResourceModel::resetModel(){return stop();} // metadata revocation only; never a GPU reset
bool ResourceModel::readyToFree()const{return held()&&stopped_&&!used_;}
}
