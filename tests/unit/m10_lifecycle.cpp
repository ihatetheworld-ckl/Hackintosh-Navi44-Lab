// CPU-only behavior tests; BSD-3-Clause. No Apple types or kernel calls.
#include "../../development/AMDRadeonRDNA4-Navi44/host/lifecycle_mock.hpp"
#include <atomic>
#include <thread>
#include <iostream>
#include <cstring>
#include <condition_variable>
#include <chrono>
using namespace NaviPlatform;using namespace NaviCore;using namespace NaviHost;
int main(){
    unsigned pass=0,fail=0;
    auto check=[&](const char*name,bool ok){std::cout<<(ok?"PASS ":"FAIL ")<<name<<'\n';ok?++pass:++fail;};
    {
        ThreadGate gate;SnapshotOwner owner(gate.access(),1);ReferenceMock resource;
        SnapshotTicket ticket{};View view{resource.bytes.data(),1};
        check("wrong_context_activation",!owner.activate(resource.ops()).ok()&&resource.retains==0);
        check("wrong_context_borrow",!owner.borrow(ticket).ok()&&!ticket.serial);
        check("wrong_context_read_clears",!owner.read(ticket,view).ok()&&!view.data&&!view.size);
        {GateScope scope(gate.access());
            check("gate_thread_entry",bool(scope));GateScope nested(gate.access());
            check("gate_nested_reentry_rejected",!nested);
            check("owner_activate_retains_once",owner.activate(resource.ops()).ok()&&resource.references==2&&resource.retains==1);
            check("duplicate_activate_rejected",!owner.activate(resource.ops()).ok()&&resource.retains==1);
            check("owner_borrow",owner.borrow(ticket).ok()&&ticket.owner==1);
            const auto copy=ticket;
            check("occupied_ticket_preserved",!owner.borrow(ticket).ok()&&ticket.serial==copy.serial);
            check("owner_read",owner.read(ticket,view).ok()&&view.data==resource.bytes.data());
            SnapshotTicket foreign=copy;foreign.owner=2;
            check("foreign_ticket_rejected",!owner.read(foreign,view).ok()&&!view.data);
            check("foreign_return_no_reference_change",!owner.giveBack(foreign).ok()&&resource.releases==0);
            check("close_with_borrow_waits",!owner.close().ok()&&resource.releases==0&&!owner.readyToFree());
            SnapshotTicket fresh{};check("borrow_after_close_rejected",!owner.borrow(fresh).ok()&&!fresh.serial);
            check("read_after_close_clears",!owner.read(ticket,view).ok()&&!view.data&&!view.size);
            check("return_completes_shutdown",owner.giveBack(ticket).ok()&&!ticket.serial&&resource.releases==1&&owner.readyToFree());
            auto duplicate=copy;
            check("double_return_rejected",!owner.giveBack(duplicate).ok()&&resource.releases==1);
            check("repeat_close_idempotent",owner.close().ok()&&owner.close().ok()&&resource.releases==1);
            check("released_owner_cannot_reopen",!owner.activate(resource.ops()).ok()&&!owner.borrow(fresh).ok());
        }
        check("destroy_ready_requires_context",!owner.readyToFree());
    }
    {
        ThreadGate gate;ReferenceMock resource;SnapshotOwner owner(gate.access(),2);
        GateScope scope(gate.access());check("prepared_owner_active",owner.activate(resource.ops(),true).ok()&&resource.prepares==1);
        SnapshotTicket tickets[SnapshotOwner::MaxLeases]{};bool borrowed=true;
        for(auto&t:tickets)borrowed&=owner.borrow(t).ok();
        check("bounded_ticket_capacity",borrowed);SnapshotTicket extra{};
        check("capacity_failure_clears_output",!owner.borrow(extra).ok()&&!extra.serial);
        check("revoke_waits_for_borrowers",!owner.revoke().ok()&&resource.completes==0&&resource.releases==0);
        View view{resource.bytes.data(),7};
        check("borrow_after_revoke_rejected",!owner.borrow(extra).ok());
        check("read_after_revoke_clears",!owner.read(tickets[0],view).ok()&&!view.data);
        bool returned=true;for(size_t i=0;i<SnapshotOwner::MaxLeases-1;++i)returned&=owner.giveBack(tickets[i]).ok();
        check("pending_missing_return_blocks_free",returned&&!owner.readyToFree()&&resource.releases==0);
        check("last_return_complete_before_release",owner.giveBack(tickets[7]).ok()&&resource.completes==1&&resource.releases==1&&owner.readyToFree());
        check("repeat_revoke_no_double_complete",owner.revoke().ok()&&resource.completes==1&&resource.releases==1);
    }
    {
        ThreadGate gate;GateScope scope(gate.access());ReferenceMock resource;SnapshotOwner owner(gate.access(),3);
        resource.failRetain=true;check("retain_failure_no_release",!owner.activate(resource.ops()).ok()&&resource.references==1&&resource.releases==0);
        check("failed_owner_cleanup",owner.close().ok()&&owner.readyToFree());
        ReferenceMock readFailure;readFailure.failView=true;SnapshotOwner viewOwner(gate.access(),4);
        check("view_failure_pairs_retain_release",!viewOwner.activate(readFailure.ops()).ok()&&readFailure.retains==1&&readFailure.releases==1);
        check("failed_view_owner_terminal",!viewOwner.activate(readFailure.ops()).ok()&&viewOwner.close().ok());
        ReferenceMock prepareFailure;prepareFailure.failPrepare=true;SnapshotOwner prepOwner(gate.access(),5);
        check("prepare_failure_does_not_complete",!prepOwner.activate(prepareFailure.ops(),true).ok()&&prepareFailure.prepares==1&&prepareFailure.completes==0&&prepareFailure.releases==1);
        check("prepare_failure_close",prepOwner.close().ok());
        ReferenceMock completion;SnapshotOwner completionOwner(gate.access(),6);
        check("completion_setup",completionOwner.activate(completion.ops(),true).ok());completion.failComplete=true;
        check("complete_failure_retains_resource",!completionOwner.close().ok()&&completion.references==2&&completion.releases==0&&!completionOwner.readyToFree());
        SnapshotTicket out{};check("failed_completion_no_new_borrows",!completionOwner.borrow(out).ok());completion.failComplete=false;
        check("complete_retry_then_release",completionOwner.close().ok()&&completion.completes==2&&completion.releases==1&&completionOwner.readyToFree());
        check("close_after_completion_no_retry",completionOwner.close().ok()&&completion.completes==2);
        ReferenceMock empty;auto ops=empty.ops();ops.complete=nullptr;SnapshotOwner pairOwner(gate.access(),7);
        check("missing_complete_rejected_before_retain",!pairOwner.activate(ops,true).ok()&&empty.retains==0&&pairOwner.close().ok());
        SnapshotOwner noGeneration(gate.access(),0);check("zero_generation_rejected",!noGeneration.activate(empty.ops()).ok()&&noGeneration.close().ok());
        ReferenceMock recycled;SnapshotOwner old(gate.access(),8),replacement(gate.access(),9);
        old.activate(recycled.ops());SnapshotTicket oldTicket{};old.borrow(oldTicket);auto stale=oldTicket;
        old.close();old.giveBack(oldTicket);replacement.activate(recycled.ops());View staleView{recycled.bytes.data(),1};
        check("generation_reuse_rejects_old_ticket",!replacement.read(stale,staleView).ok()&&!staleView.data&&replacement.close().ok());
    }
    {
        ThreadGate gate;GateScope scope(gate.access());
        for(unsigned variant=0;variant<4;++variant){
            ReferenceMock resource;resource.useOverride=true;
            resource.overrideView=variant==0?View{nullptr,9}:variant==1?View{resource.bytes.data(),0}:variant==2?View{resource.bytes.data(),SnapshotOwner::MaxBytes+1}:View{reinterpret_cast<const uint8_t*>(UINTPTR_MAX-1),8};
            SnapshotOwner owner(gate.access(),10+variant);
            const bool rejected=!owner.activate(resource.ops()).ok()&&resource.releases==1&&resource.references==1&&owner.close().ok();
            check(variant==0?"null_view_rejected":variant==1?"empty_view_rejected":variant==2?"oversized_view_rejected":"address_wrap_rejected",rejected);
        }
        ReferenceMock first,second;SnapshotOwner a(gate.access(),20),b(gate.access(),21);
        check("multi_resource_partial_setup",a.activate(first.ops()).ok());second.failView=true;
        check("multi_resource_failure_rollback",!b.activate(second.ops()).ok()&&a.close().ok()&&b.close().ok()&&first.releases==1&&second.releases==1);
    }
    {
        ThreadGate gate;GateScope scope(gate.access());ReferenceMock resource;SnapshotOwner owner(gate.access(),30);
        check("creator_lifetime_setup",owner.activate(resource.ops()).ok());SnapshotTicket t{};owner.borrow(t);
        ReferenceMock::release(&resource);View v{};
        check("creator_release_keeps_borrow_alive",resource.references==1&&resource.alive&&owner.read(t,v).ok());
        owner.revoke();check("resource_survives_shutdown_barrier",resource.alive&&resource.references==1);
        check("final_borrow_return_releases_last_reference",owner.giveBack(t).ok()&&!resource.alive&&resource.references==0);
    }
    {
        ThreadGate gate;GateScope scope(gate.access());ReferenceMock resource;SnapshotOwner owner(gate.access(),40);
        owner.activate(resource.ops());NodePool pool;unsigned logs=0;
        Contract c{{},{&logs,[](void*ctx,Result){++*static_cast<unsigned*>(ctx);}},owner.snapshots(),pool.contract(),owner.execution()};
        // Reenter gate via validateSnapshot is correctly rejected while already held.
        check("nested_parser_context_rejected",validateSnapshot(c,Asic::Target::Gfx1200).code==Error::Protocol&&logs==0);
        View v{};auto callbacks=owner.snapshots();check("legacy_borrow_callback",callbacks.borrow(callbacks.context,SnapshotKind::ElfFile,v).ok());
        View wrong=v;--wrong.size;callbacks.release(callbacks.context,wrong);
        check("foreign_legacy_release_blocks_cleanup",!owner.close().ok()&&!owner.readyToFree());
        callbacks.release(callbacks.context,v);callbacks.release(callbacks.context,v);
        check("legacy_valid_release_once",resource.releases==1&&owner.readyToFree());
    }
    {
        ThreadGate gate;ReferenceMock resource;SnapshotOwner owner(gate.access(),41);NodePool pool;unsigned logs=0;
        {GateScope scope(gate.access());owner.activate(resource.ops());}
        Contract c{{},{&logs,[](void*ctx,Result){++*static_cast<unsigned*>(ctx);}},owner.snapshots(),pool.contract(),owner.execution()};
        check("existing_parser_bridge_cleanup",!validateSnapshot(c,Asic::Target::Gfx1200).ok()&&logs==1);
        {GateScope scope(gate.access());OwnerState state;size_t leases=1;
            check("parser_returns_snapshot_ticket",owner.inspect(state,leases).ok()&&leases==0&&owner.close().ok()&&resource.releases==1);}
        ThreadGate::interruptContext(true);SnapshotTicket t{};
        check("interrupt_gate_rejected",!GateScope(gate.access())&&!owner.borrow(t).ok());ThreadGate::interruptContext(false);
    }
    {
        ThreadGate gate;GateScope scope(gate.access());ReferenceMock resource;SnapshotOwner owner(gate.access(),50);
        struct Hook {SnapshotOwner*owner;bool denied{false};} hook{&owner};
        resource.hook=&hook;resource.onRelease=[](void*ctx){auto&h=*static_cast<Hook*>(ctx);h.denied=!h.owner->close().ok();};
        owner.activate(resource.ops());check("release_callback_reentry_rejected",owner.close().ok()&&hook.denied&&resource.releases==1);
    }
    {
        NodePool pool;auto ops=pool.contract();Node foreign[1]{};Node*p=ops.acquire(ops.context,8);
        check("pool_acquire_constructed_nodes",p!=nullptr);ops.release(ops.context,foreign,8);
        check("pool_foreign_return_does_not_unlock",!ops.acquire(ops.context,8));ops.release(ops.context,p,7);
        check("pool_wrong_count_does_not_unlock",!ops.acquire(ops.context,8));p[0].number=99;ops.release(ops.context,p,8);
        p=ops.acquire(ops.context,8);check("pool_correct_return_clears_nodes",p&&p[0].number==0);ops.release(ops.context,p,8);ops.release(ops.context,p,8);
        check("pool_duplicate_return_safe",ops.acquire(ops.context,1)!=nullptr);ops.release(ops.context,p,1);
        check("pool_capacity_rejected",!ops.acquire(ops.context,513));
    }
    {
        struct Memory {alignas(16) uint8_t bytes[32]{};Lease*lease{nullptr};unsigned frees{0},allocations{0};bool nestedRejected{false};} memory;
        MemoryOps ops{&memory,[](void*ctx,size_t,size_t)->void*{auto&m=*static_cast<Memory*>(ctx);++m.allocations;if(m.allocations==1)m.nestedRejected=!m.lease->open(1,1);return m.bytes;},
            [](void*ctx,void*,size_t){auto&m=*static_cast<Memory*>(ctx);++m.frees;if(m.frees==1)m.lease->close();}};
        Lease lease(ops);memory.lease=&lease;
        check("lease_allocate_callback_reentry",lease.open(16,16)&&memory.nestedRejected&&memory.allocations==1);lease.close();
        check("lease_recursive_release_once",memory.frees==1&&!lease.data()&&!lease.view().size);
        MemoryOps wrap{&memory,[](void*,size_t,size_t)->void*{return reinterpret_cast<void*>(UINTPTR_MAX-1);},[](void*ctx,void*,size_t){++static_cast<Memory*>(ctx)->frees;}};
        Lease bad(wrap);check("lease_address_wrap_releases",!bad.open(8,1)&&memory.frees==2&&!bad.data());
        MemoryOps align{&memory,[](void*ctx,size_t,size_t)->void*{return static_cast<Memory*>(ctx)->bytes+1;},wrap.release};
        Lease misaligned(align);check("lease_alignment_rejects_and_releases",!misaligned.open(16,16)&&memory.frees==3);
    }
    {
        bool invariant=true;
        for(unsigned i=0;i<600;++i){
            ThreadGate gate;GateScope scope(gate.access());ReferenceMock r;SnapshotOwner owner(gate.access(),1000+i);
            r.failRetain=i%5==0;r.failView=i%5==1;r.failPrepare=i%5==2;
            bool active=owner.activate(r.ops(),true).ok();SnapshotTicket t{};
            if(active){invariant&=owner.borrow(t).ok();owner.revoke();invariant&=owner.giveBack(t).ok();}
            invariant&=owner.close().ok()&&owner.readyToFree()&&r.references==1&&r.retains==r.releases;
        }
        check("bounded_initialization_failure_injection",invariant);
        std::cout<<"M10_FAILURE_INJECTION inputs=600 invariants="<<(invariant?"PASS":"FAIL")<<'\n';
    }
    {
        ThreadGate gate;ReferenceMock resource;SnapshotOwner owner(gate.access(),2000);
        {GateScope scope(gate.access());owner.activate(resource.ops(),true);}
        std::atomic<unsigned> successes{0},denied{0},errors{0};std::atomic<bool> firstReady{false},shutdown{false};
        std::mutex signalMutex;std::condition_variable signal;
        auto worker=[&](){
            for(unsigned i=0;i<120;++i){
                GateScope scope(gate.access());if(!scope){++errors;continue;}
                SnapshotTicket t{};auto r=owner.borrow(t);
                if(r.ok()){View v{};if(!owner.read(t,v).ok()||!v.data||!owner.giveBack(t).ok())++errors;else ++successes;}
                else ++denied;
            }
        };
        // Hold one ticket while stop requests shutdown; no raw pointer access outside gate.
        std::thread borrower([&](){SnapshotTicket t{};
            {GateScope scope(gate.access());if(!owner.borrow(t).ok())++errors;}
            {std::unique_lock<std::mutex> lock(signalMutex);firstReady=true;signal.notify_all();
                if(!signal.wait_for(lock,std::chrono::seconds(2),[&](){return shutdown.load();}))++errors;}
            {GateScope scope(gate.access());View v{resource.bytes.data(),1};
                if(shutdown&&owner.read(t,v).ok())++errors;
                if(!owner.giveBack(t).ok())++errors;}
        });
        {std::unique_lock<std::mutex> lock(signalMutex);
            if(!signal.wait_for(lock,std::chrono::seconds(2),[&](){return firstReady.load();}))++errors;}
        std::thread a(worker),b(worker);
        {GateScope scope(gate.access());owner.revoke();}
        {std::lock_guard<std::mutex> lock(signalMutex);shutdown=true;signal.notify_all();}
        a.join();b.join();borrower.join();
        {GateScope scope(gate.access());
            check("bounded_concurrency_shutdown_barrier",firstReady&&owner.close().ok()&&owner.readyToFree()&&errors==0&&resource.releases==1&&resource.completes==1);
            check("bounded_concurrency_counts",successes+denied==240);}
        std::cout<<"M10_CONCURRENCY attempts=240 accepted="<<successes<<" rejected="<<denied<<" errors="<<errors<<'\n';
    }
    std::cout<<"SUMMARY "<<pass<<' '<<fail<<'\n';return fail?1:0;
}
