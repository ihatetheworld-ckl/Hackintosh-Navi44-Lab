// CPU-only M11 behavior tests; BSD-3-Clause. No IOKit objects or native calls.
#include "../../development/AMDRadeonRDNA4-Navi44/host/lifecycle_mock.hpp"
#include "../../development/AMDRadeonRDNA4-Navi44/platform/shutdown.hpp"
#include <iostream>
#include <thread>
#include <atomic>
#include <new>
#include <condition_variable>
#include <chrono>
using namespace NaviCore;using namespace NaviPlatform;using namespace NaviHost;
int main(){
    unsigned pass=0,fail=0;
    auto check=[&](const char*n,bool b){std::cout<<(b?"PASS ":"FAIL ")<<n<<'\n';b?++pass:++fail;};
    {
        ThreadGate gate;ReferenceMock a,b;SnapshotOwner oa(gate.access(),1),ob(gate.access(),1);
        GateScope hold(gate.access());oa.activate(a.ops());ob.activate(b.ops());SnapshotTicket ta{},tb{};oa.borrow(ta);ob.borrow(tb);auto saved=ta;View v{};
        check("duplicate_generation_cross_owner_read_denied",!ob.read(ta,v).ok()&&!v.data);
        check("duplicate_generation_cross_owner_return_preserved",!ob.giveBack(ta).ok()&&ta.identity==saved.identity&&ta.serial==saved.serial);
        check("legitimate_ticket_survives_foreign_return",oa.read(ta,v).ok()&&ob.read(tb,v).ok());
        SnapshotTicket identityOnly{};identityOnly.identity=&oa;
        check("occupied_identity_not_overwritten",!ob.borrow(identityOnly).ok()&&identityOnly.identity==&oa);
        check("own_tickets_return_once",oa.giveBack(ta).ok()&&ob.giveBack(tb).ok()&&oa.close().ok()&&ob.close().ok()&&a.releases==1&&b.releases==1);
    }
    {
        ThreadGate gate;GenerationClock clock(gate.access());uint64_t one=0,two=0;
        check("generation_wrong_context",!clock.issue(one).ok()&&!one);
        GateScope hold(gate.access());check("generation_monotonic",clock.issue(one).ok()&&clock.issue(two).ok()&&one==1&&two==2);
        check("generation_occupied_preserved",!clock.issue(one).ok()&&one==1);
        GenerationClock last(gate.access(),UINT64_MAX-1);uint64_t x=0,y=0;
        auto invalid=gate.access();invalid.execution.leave=nullptr;GenerationClock bad(invalid);
        check("generation_incomplete_gate_denied",!bad.issue(y).ok()&&!y);
        check("generation_last_safe_value",last.issue(x).ok()&&x==UINT64_MAX-1);
        check("generation_exhaustion_no_wrap",!last.issue(y).ok()&&!y&&!last.issue(y).ok());
        // Actual address reuse under one persistent issuer: stale generation fails.
        alignas(SnapshotOwner) unsigned char bytes[sizeof(SnapshotOwner)];ReferenceMock r;
        auto*o=new(bytes)SnapshotOwner(gate.access(),one);o->activate(r.ops());SnapshotTicket t{};o->borrow(t);auto stale=t;o->giveBack(t);o->close();o->~SnapshotOwner();
        o=new(bytes)SnapshotOwner(gate.access(),two);o->activate(r.ops());o->borrow(t);View v{};
        check("same_address_stale_generation_rejected",!o->read(stale,v).ok()&&!v.data&&!o->giveBack(stale).ok());
        check("reused_storage_current_ticket_valid",o->read(t,v).ok()&&o->giveBack(t).ok()&&o->close().ok());o->~SnapshotOwner();
    }
    {
        ThreadGate gate,other;ReferenceMock a,b;SnapshotOwner oa(gate.access(),11),ob(gate.access(),12),foreign(other.access(),13);ShutdownBarrier group(gate.access());
        check("bind_wrong_thread",!group.bind(oa).ok());GateScope hold(gate.access());
        check("bind_wrong_gate",!group.bind(foreign).ok());check("bind_owner",group.bind(oa).ok());check("duplicate_bind_denied",!group.bind(oa).ok());check("bind_second",group.bind(ob).ok());
        check("start_incomplete_denied",!group.start().ok());oa.activate(a.ops(),true);ob.activate(b.ops(),true);
        check("active_start",group.start().ok());check("duplicate_start_denied",!group.start().ok());check("binding_after_start_denied",!group.bind(foreign).ok());check("poll_before_stop_denied",!group.poll().ok());
        SnapshotTicket t{};check("active_ticket",group.borrow(0,t).ok());View v{};check("active_read",group.read(0,t,v).ok());
        check("stop_waits_for_live_ticket",!group.stop().ok()&&a.releases==0&&b.releases==1&&!group.readyToFree());
        ShutdownState state{};size_t n=0;unsigned retries=0;group.inspect(state,n,retries);check("draining_count",state==ShutdownState::Draining&&n==1&&retries==0);
        SnapshotTicket fresh{};check("stop_blocks_new_ticket",!group.borrow(1,fresh).ok()&&!fresh.serial);check("stop_blocks_read_clears_view",!group.read(0,t,v).ok()&&!v.data);
        check("stop_idempotent_pending",!group.stop().ok()&&a.releases==0&&b.releases==1);
        const auto copy=t;check("wrong_owner_return_preserves_obligation",!group.giveBack(1,t).ok()&&t.serial==copy.serial);
        check("out_of_range_return_preserves_obligation",!group.giveBack(8,t).ok()&&t.serial==copy.serial);
        check("old_ticket_return_during_drain",group.giveBack(0,t).ok()&&a.releases==1&&a.completes==1);
        check("final_poll_releases_storage",group.poll().ok()&&group.readyToFree());check("repeat_stop_no_double_release",group.stop().ok()&&a.releases==1&&b.releases==1);
        auto duplicate=copy;check("double_return_denied",!group.giveBack(0,duplicate).ok());
        group.inspect(state,n,retries);check("released_state",state==ShutdownState::Released&&!n);
    }
    {
        ThreadGate gate;GateScope hold(gate.access());ReferenceMock good,bad;bad.failView=true;SnapshotOwner a(gate.access(),21),b(gate.access(),22);ShutdownBarrier g(gate.access());g.bind(a);g.bind(b);a.activate(good.ops());b.activate(bad.ops());
        check("partial_init_start_denied",!g.start().ok());check("partial_init_reverse_cleanup",g.stop().ok()&&g.readyToFree()&&good.releases==1&&bad.releases==1);
        SnapshotTicket t{};check("cleanup_cannot_restart",!g.start().ok()&&!g.borrow(0,t).ok());
    }
    {
        ThreadGate gate;GateScope hold(gate.access());ReferenceMock r;SnapshotOwner o(gate.access(),31);ShutdownBarrier g(gate.access());g.bind(o);o.activate(r.ops(),true);g.start();r.failComplete=true;
        check("complete_failure_preserves_reference",!g.stop().ok()&&r.references==2&&r.releases==0&&!g.readyToFree());
        for(unsigned i=1;i<ShutdownBarrier::MaxCleanupFailures;++i)g.poll();
        unsigned count=r.completes;bool denied=true;for(unsigned i=0;i<50;++i)denied&=!g.poll().ok();
        check("cleanup_retry_budget_bounded",denied&&count==4&&r.completes==count&&r.references==2);
        r.failComplete=false;check("budget_exhaustion_never_silently_frees",!g.poll().ok()&&!g.readyToFree()&&r.releases==0);
        // Explicit owner recovery after exhaustion is separate from automatic retry.
        check("explicit_owner_recovery",o.close().ok()&&g.poll().ok()&&g.readyToFree()&&r.releases==1);
    }
    {
        ThreadGate gate;GateScope hold(gate.access());ReferenceMock r;SnapshotOwner o(gate.access(),41);ShutdownBarrier g(gate.access());g.bind(o);o.activate(r.ops(),true);g.start();r.failComplete=true;g.stop();r.failComplete=false;
        check("cleanup_retry_within_budget",g.poll().ok()&&g.readyToFree()&&r.completes==2&&r.releases==1);
        ShutdownBarrier empty(gate.access());check("empty_activation_denied",!empty.start().ok());check("empty_stop_free",empty.stop().ok()&&empty.readyToFree());
        struct Hook{ShutdownBarrier*g;bool denied{false};} hook{&g};
        ReferenceMock reentrant;SnapshotOwner oo(gate.access(),42);ShutdownBarrier gg(gate.access());hook.g=&gg;reentrant.hook=&hook;
        reentrant.onRelease=[](void*c){auto&h=*static_cast<Hook*>(c);SnapshotTicket t{};h.denied=!h.g->stop().ok()&&!h.g->borrow(0,t).ok();};
        gg.bind(oo);oo.activate(reentrant.ops());gg.start();check("shutdown_release_callback_reentry",gg.stop().ok()&&hook.denied&&reentrant.releases==1);
        ThreadGate::interruptContext(true);SnapshotTicket t{};check("interrupt_shutdown_rejected",!gg.stop().ok()&&!gg.borrow(0,t).ok()&&!gg.readyToFree());ThreadGate::interruptContext(false);
    }
    {
        ThreadGate gate;GateScope hold(gate.access());ShutdownBarrier group(gate.access());
        SnapshotOwner owners[]={SnapshotOwner(gate.access(),61),SnapshotOwner(gate.access(),62),SnapshotOwner(gate.access(),63),SnapshotOwner(gate.access(),64),SnapshotOwner(gate.access(),65),SnapshotOwner(gate.access(),66),SnapshotOwner(gate.access(),67),SnapshotOwner(gate.access(),68),SnapshotOwner(gate.access(),69)};
        bool bound=true;for(unsigned i=0;i<8;++i)bound=group.bind(owners[i]).ok()&&bound;
        check("owner_capacity_eight",bound);check("owner_capacity_overflow_denied",!group.bind(owners[8]).ok());
        check("unactivated_bound_owners_cleanup",group.stop().ok()&&group.readyToFree());
        NodePool pool;auto ops=pool.contract();auto*p=ops.acquire(ops.context,7);
        check("scratch_storage_not_idle_while_borrowed",p&&!pool.idle());ops.release(ops.context,p,6);
        check("scratch_wrong_return_keeps_storage_live",!pool.idle());ops.release(ops.context,p,7);check("scratch_final_return_idle",pool.idle());
    }
    {
        // Deterministic partial-init/complete failures, never native allocation.
        bool ok=true;for(unsigned i=0;i<400;++i){ThreadGate gate;GateScope hold(gate.access());GenerationClock clock(gate.access());uint64_t id=0;clock.issue(id);ReferenceMock r;SnapshotOwner o(gate.access(),id);ShutdownBarrier g(gate.access());g.bind(o);
            r.failRetain=i%4==0;r.failView=i%4==1;r.failPrepare=i%4==2;bool active=o.activate(r.ops(),true).ok();
            if(active){ok&=g.start().ok();SnapshotTicket t{};g.borrow(0,t);ok&=!g.stop().ok()&&g.giveBack(0,t).ok();}
            ok&=g.stop().ok()&&g.readyToFree()&&r.references==1&&r.releases==(r.failRetain?0u:1u);
        }check("bounded_400_initialization_failures",ok);
    }
    {
        // Two user threads, finite 320 attempts, stop races with acquisition.
        ThreadGate gate;ReferenceMock r;SnapshotOwner o(gate.access(),51);ShutdownBarrier g(gate.access());
        {GateScope hold(gate.access());g.bind(o);o.activate(r.ops(),true);g.start();}
        std::atomic<unsigned> errors{0},started{0},acquired{0},denied{0},ready{0};std::atomic<bool> stopped{false};
        std::mutex signalMutex;std::condition_variable signal;
        auto worker=[&](){++started;for(unsigned i=0;i<160;++i){SnapshotTicket t{};
            {GateScope hold(gate.access());if(g.borrow(0,t).ok()){++acquired;View v{};if(!g.read(0,t,v).ok())++errors;}else ++denied;}
            if(i==0){++ready;std::unique_lock<std::mutex> lock(signalMutex);signal.notify_all();
                if(!signal.wait_for(lock,std::chrono::seconds(2),[&](){return stopped.load();}))++errors;}
            std::this_thread::yield();if(t.serial){GateScope hold(gate.access());if(!g.giveBack(0,t).ok())++errors;}
        }};
        std::thread a(worker),b(worker);
        {std::unique_lock<std::mutex> lock(signalMutex);if(!signal.wait_for(lock,std::chrono::seconds(2),[&](){return ready==2;}))++errors;}
        {GateScope hold(gate.access());if(g.stop().ok()||r.releases)++errors;}
        {std::lock_guard<std::mutex> lock(signalMutex);stopped=true;signal.notify_all();}a.join();b.join();
        {GateScope hold(gate.access());check("bounded_stop_borrow_race",g.poll().ok()&&g.readyToFree()&&started==2&&acquired==2&&denied==318&&errors==0&&r.releases==1&&r.completes==1);}
        check("free_barrier_requires_gate",!g.readyToFree());
        std::cout<<"M11_CONCURRENCY attempts=320 acquired="<<acquired<<" denied="<<denied<<" errors="<<errors<<'\n';
    }
    check("hardware_capability_remains_closed",!Asic::hardwareInitializationAllowed()&&!NaviCore::hardwareAllowed());
    std::cout<<"SUMMARY "<<pass<<' '<<fail<<'\n';return fail?1:0;
}
