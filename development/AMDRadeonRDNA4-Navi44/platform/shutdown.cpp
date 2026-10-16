#include "shutdown.hpp"
namespace NaviPlatform {
using namespace NaviCore;
namespace {Result denied(){return failure("shutdown_context_or_reentry",Error::Protocol);}}
Result GenerationClock::issue(uint64_t&out){
    if(out)return failure("generation_output_occupied",Error::Protocol);
    if(!access_.execution.enter||!access_.execution.leave||!access_.isHeld||!access_.isHeld(access_.execution.context))return denied();
    if(!next_||next_==UINT64_MAX)return failure("generation_exhausted",Error::Budget);
    out=next_++;return success();
}
bool ShutdownBarrier::held()const{return access_.execution.enter&&access_.execution.leave&&access_.isHeld&&access_.isHeld(access_.execution.context);}
bool ShutdownBarrier::begin(){if(!held()||operation_)return false;operation_=true;return true;}
Result ShutdownBarrier::bind(SnapshotOwner&o){
    if(!begin())return denied();
    const auto e=o.execution();Result r=success();
    if(state_!=ShutdownState::Created||count_==8||e.context!=access_.execution.context||
       e.enter!=access_.execution.enter||e.leave!=access_.execution.leave)r=failure("shutdown_binding",Error::Protocol);
    else{
        for(size_t i=0;i<count_;++i)if(owners_[i]==&o){end();return failure("shutdown_duplicate_owner",Error::Protocol);}
        owners_[count_++]=&o;
    }
    end();return r;
}
Result ShutdownBarrier::start(){
    if(!begin())return denied();Result r=success();
    if((state_!=ShutdownState::Created&&state_!=ShutdownState::Initialized)||!count_)r=failure("shutdown_start_state",Error::Protocol);
    else for(size_t i=0;i<count_;++i){OwnerState s{};size_t leases=0;r=owners_[i]->inspect(s,leases);
        if(!r.ok()||s!=OwnerState::Active){r=failure("shutdown_partial_initialization",Error::Protocol);break;}}
    if(r.ok())state_=ShutdownState::Active;end();return r;
}
Result ShutdownBarrier::initialize(){
    if(!begin())return denied();Result r=success();
    if(state_!=ShutdownState::Created||!count_){end();return failure("shutdown_initialize_state",Error::Protocol);}
    for(size_t i=0;i<count_;++i){OwnerState s{};size_t n=0;r=owners_[i]->inspect(s,n);
        if(!r.ok()||s!=OwnerState::Active){r=failure("shutdown_initialize_owner",Error::Protocol);break;}}
    state_=r.ok()?ShutdownState::Initialized:ShutdownState::Failed;end();return r;
}
Result ShutdownBarrier::consume(size_t i,InputConsumer consumer){
    if(!begin())return denied();
    Result r=state_==ShutdownState::Active&&i<count_?owners_[i]->consume(consumer):failure("shutdown_scope_not_active",Error::Protocol);
    end();return r;
}
Result ShutdownBarrier::borrow(size_t i,SnapshotTicket&t){
    if(!begin())return denied();
    Result r=state_==ShutdownState::Active&&i<count_?owners_[i]->borrow(t):failure("shutdown_no_new_ticket",Error::Protocol);
    end();return r;
}
Result ShutdownBarrier::read(size_t i,const SnapshotTicket&t,View&out){
    out={};if(!begin())return denied();
    Result r=state_==ShutdownState::Active&&i<count_?owners_[i]->read(t,out):failure("shutdown_read_closed",Error::Protocol);
    end();return r;
}
Result ShutdownBarrier::giveBack(size_t i,SnapshotTicket&t){
    if(!begin())return denied();
    Result r=i<count_?owners_[i]->giveBack(t):failure("shutdown_wrong_owner",Error::Protocol);
    end();return r;
}
Result ShutdownBarrier::drainHeld(){
    bool pending=false;Result error=success();
    // Examine all owners before choosing a result; one pending owner must not
    // keep unrelated owners active. Never wait or block while holding the gate.
    for(size_t i=count_;i>0;--i){
        auto&o=*owners_[i-1];if(o.readyToFree())continue;
        OwnerState state{};size_t leases=0;Result r=o.inspect(state,leases);
        if(!r.ok()){error=r;continue;}
        // close invalidates new access even if an outstanding borrower exists.
        if(failures_>=MaxCleanupFailures&&state==OwnerState::Failed&&!leases){error=failure("shutdown_retry_budget",Error::Budget);continue;}
        r=o.close();
        if(!r.ok()){if(leases)pending=true;else error=r;}
    }
    // Re-check after cleanup, including after the final ticket's giveBack.
    bool ready=true;for(size_t i=0;i<count_;++i)ready=owners_[i]->readyToFree()&&ready;
    if(ready){state_=ShutdownState::Released;return success();}
    if(!error.ok()){if(failures_<MaxCleanupFailures)++failures_;state_=ShutdownState::Failed;return error;}
    state_=ShutdownState::Draining;
    return failure(pending?"shutdown_borrowers_pending":"shutdown_not_drained",Error::Protocol);
}
Result ShutdownBarrier::stop(){
    if(!begin())return denied();if(state_==ShutdownState::Released){end();return success();}
    // Transition first, before any foreign complete/release callback can reenter.
    if(state_==ShutdownState::Created||state_==ShutdownState::Initialized||state_==ShutdownState::Active)state_=ShutdownState::Stopping;
    Result r=drainHeld();end();return r;
}
Result ShutdownBarrier::poll(){
    if(!begin())return denied();
    if(state_==ShutdownState::Created||state_==ShutdownState::Initialized||state_==ShutdownState::Active){end();return failure("shutdown_poll_state",Error::Protocol);}
    Result r=state_==ShutdownState::Released?success():drainHeld();end();return r;
}
bool ShutdownBarrier::readyToFree()const{
    if(!held()||operation_||state_!=ShutdownState::Released)return false;
    for(size_t i=0;i<count_;++i)if(!owners_[i]->readyToFree())return false;
    return true;
}
Result ShutdownBarrier::inspect(ShutdownState&s,size_t&borrowers,unsigned&failures)const{
    s=ShutdownState::Failed;borrowers=0;failures=0;if(!held()||operation_)return denied();
    for(size_t i=0;i<count_;++i){OwnerState os{};size_t n=0;Result r=owners_[i]->inspect(os,n);if(!r.ok())return r;borrowers+=n;}
    s=state_;failures=failures_;return success();
}
}
