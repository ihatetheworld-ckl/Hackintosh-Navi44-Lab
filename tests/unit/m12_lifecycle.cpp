// CPU-only scoped access and explicit initialization tests; BSD-3-Clause.
#include "../../development/AMDRadeonRDNA4-Navi44/host/lifecycle_mock.hpp"
#include "../../development/AMDRadeonRDNA4-Navi44/platform/shutdown.hpp"
#include <iostream>
#include <type_traits>
#include <thread>
#include <atomic>
#include <condition_variable>
#include <chrono>
using namespace NaviPlatform;using namespace NaviCore;using namespace NaviHost;
static_assert(!std::is_copy_constructible<ScopedInput>::value,"scope cannot escape by value");
static_assert(!std::is_move_constructible<ScopedInput>::value,"scope cannot move out");
static_assert(!std::is_destructible<ScopedInput>::value,"consumer cannot destroy caller scope");
struct ConsumerContext {
    SnapshotOwner*owner;ShutdownBarrier*barrier;ReferenceMock*resource;
    bool fail{false},bounds{false},reentry{false},context{false},copied{false},byteAlias{false};unsigned callbacks{0};
    uint8_t destination[16]{};
    static Result consume(void*ptr,const ScopedInput&input)noexcept{
        auto&c=*static_cast<ConsumerContext*>(ptr);++c.callbacks;size_t n=0;
        if(!input.length(n).ok()||n!=4096)return failure("scope_length");
        uint8_t value=99;c.copied=input.byte(7,value).ok()&&value==7&&input.copy(0,c.destination,16).ok();
        for(unsigned i=0;i<16;++i)c.copied=c.copied&&c.destination[i]==i;
        uint8_t unchanged=42;
        c.byteAlias=!input.byte(0,c.resource->bytes[7]).ok()&&c.resource->bytes[7]==7;
        c.bounds=!input.copy(4096,&unchanged,1).ok()&&unchanged==42&&!input.copy(SIZE_MAX,&unchanged,1).ok()&&
            !input.copy(0,nullptr,1).ok()&&!input.copy(0,reinterpret_cast<uint8_t*>(UINTPTR_MAX-2),8).ok()&&input.copy(4096,nullptr,0).ok()&&
            !input.copy(0,c.resource->bytes.data()+1,4).ok()&&c.resource->bytes[1]==1;
        SnapshotTicket t{};View v{};
        c.reentry=!c.owner->consume({&c,consume}).ok()&&!c.owner->close().ok()&&!c.owner->revoke().ok()&&!c.owner->borrow(t).ok()&&!c.owner->read(t,v).ok();
        if(c.barrier)c.reentry=c.reentry&&!c.barrier->stop().ok()&&!c.barrier->consume(0,{&c,consume}).ok();
        ThreadGate::interruptContext(true);n=100;c.context=!input.length(n).ok()&&!n&&!input.copy(0,c.destination,1).ok();ThreadGate::interruptContext(false);
        return c.fail?failure("deliberate_consumer_failure"):success();
    }
};
int main(){unsigned pass=0,fail=0;
    auto check=[&](const char*n,bool b){std::cout<<(b?"PASS ":"FAIL ")<<n<<'\n';b?++pass:++fail;};
    {
        ThreadGate gate;ReferenceMock r;for(size_t i=0;i<r.bytes.size();++i)r.bytes[i]=static_cast<uint8_t>(i);
        SnapshotOwner owner(gate.access(),1);ShutdownBarrier barrier(gate.access());ConsumerContext c{&owner,&barrier,&r};
        check("scope_wrong_context_denied",!owner.consume({&c,ConsumerContext::consume}).ok()&&c.callbacks==0);
        GateScope hold(gate.access());barrier.bind(owner);owner.activate(r.ops(),true);
        check("storage_initialize",barrier.initialize().ok());ShutdownState state{};size_t leases=0;unsigned f=0;barrier.inspect(state,leases,f);
        check("initialized_state",state==ShutdownState::Initialized&&!leases);
        check("initialized_scope_denied",!barrier.consume(0,{&c,ConsumerContext::consume}).ok()&&!c.callbacks);
        SnapshotTicket t{};check("initialized_ticket_denied",!barrier.borrow(0,t).ok());
        check("initialized_poll_denied",!barrier.poll().ok());check("duplicate_initialize_denied",!barrier.initialize().ok());
        check("explicit_storage_start",barrier.start().ok());check("automatic_scope_success",barrier.consume(0,{&c,ConsumerContext::consume}).ok());
        check("scope_bounded_copy",c.copied);check("scope_bounds_and_immutable_source",c.bounds);check("scope_callback_reentry_denied",c.reentry);check("scope_wrong_thread_context_denied",c.context);
        check("scope_byte_alias_preserves_source",c.byteAlias);
        OwnerState os{};owner.inspect(os,leases);check("automatic_ticket_return",leases==0&&r.references==2&&r.releases==0);
        c.fail=true;check("consumer_error_preserved",!barrier.consume(0,{&c,ConsumerContext::consume}).ok());owner.inspect(os,leases);check("consumer_error_returns_ticket",leases==0&&r.references==2);
        check("missing_consumer_no_ticket",!barrier.consume(0,{}).ok());check("wrong_owner_index_no_callback",!barrier.consume(8,{&c,ConsumerContext::consume}).ok()&&c.callbacks==2);
        check("stop_scope_cleanup_once",barrier.stop().ok()&&barrier.readyToFree()&&r.completes==1&&r.releases==1);
        check("scope_after_stop_denied",!barrier.consume(0,{&c,ConsumerContext::consume}).ok()&&c.callbacks==2);
        check("released_storage_cannot_initialize",!barrier.initialize().ok()&&!barrier.start().ok());
    }
    {
        ThreadGate gate;GateScope hold(gate.access());ReferenceMock r;for(size_t i=0;i<r.bytes.size();++i)r.bytes[i]=static_cast<uint8_t>(i);
        SnapshotOwner a(gate.access(),7),b(gate.access(),7);a.activate(r.ops());b.activate(r.ops());ConsumerContext c{&a,nullptr,&r};SnapshotTicket ta{},tb{};a.borrow(ta);b.borrow(tb);
        check("foreign_ticket_scope_denied",!a.withInput(tb,{&c,ConsumerContext::consume}).ok()&&c.callbacks==0);
        check("explicit_ticket_scope_success",a.withInput(ta,{&c,ConsumerContext::consume}).ok()&&c.callbacks==1);
        OwnerState state{};size_t n=0;a.inspect(state,n);check("explicit_ticket_retained",n==1);
        const auto stale=ta;a.giveBack(ta);check("stale_ticket_scope_denied",!a.withInput(stale,{&c,ConsumerContext::consume}).ok());b.giveBack(tb);a.close();b.close();
        check("cross_owner_scope_reference_pairs",r.retains==2&&r.releases==2&&r.references==1);
    }
    {
        ThreadGate gate;GateScope hold(gate.access());ReferenceMock r;SnapshotOwner owner(gate.access(),20);ShutdownBarrier g(gate.access());g.bind(owner);owner.activate(r.ops());
        check("stop_initialized_without_start",g.initialize().ok()&&g.stop().ok()&&g.readyToFree()&&r.releases==1);
        SnapshotOwner uninitialized(gate.access(),21);ShutdownBarrier bad(gate.access());bad.bind(uninitialized);
        check("partial_initialization_fails",!bad.initialize().ok());ShutdownState state{};size_t n=0;unsigned f=0;bad.inspect(state,n,f);
        check("failed_initialized_state",state==ShutdownState::Failed&&!n);check("failed_initialization_cannot_start",!bad.start().ok());
        check("failed_initialized_cleanup",bad.stop().ok()&&bad.readyToFree());
    }
    {
        // 300 finite error callbacks must not exhaust eight ticket slots.
        ThreadGate gate;GateScope hold(gate.access());ReferenceMock r;for(size_t i=0;i<r.bytes.size();++i)r.bytes[i]=static_cast<uint8_t>(i);
        SnapshotOwner o(gate.access(),30);ShutdownBarrier g(gate.access());g.bind(o);o.activate(r.ops());g.initialize();g.start();ConsumerContext c{&o,&g,&r};c.fail=true;bool ok=true;
        for(unsigned i=0;i<300;++i){ok=(!g.consume(0,{&c,ConsumerContext::consume}).ok())&&ok;OwnerState state{};size_t n=0;o.inspect(state,n);ok=(!n&&r.references==2)&&ok;}
        check("bounded_300_callback_error_cleanup",ok&&c.callbacks==300&&g.stop().ok()&&g.readyToFree()&&r.releases==1);
    }
    {
        ThreadGate gate;ReferenceMock r;SnapshotOwner o(gate.access(),40);ShutdownBarrier g(gate.access());
        {GateScope hold(gate.access());g.bind(o);o.activate(r.ops(),true);g.initialize();g.start();}
        std::mutex mutex;std::condition_variable signal;bool entered=false,allowReturn=false;std::atomic<unsigned> accepted{0},denied{0},errors{0};
        struct Slow {std::mutex*m;std::condition_variable*s;bool*entered,*allow;std::atomic<unsigned>*errors;} slow{&mutex,&signal,&entered,&allowReturn,&errors};
        auto callback=[](void*p,const ScopedInput&input)noexcept->Result{auto&c=*static_cast<Slow*>(p);size_t n=0;if(!input.length(n).ok())++*c.errors;
            std::unique_lock<std::mutex> lock(*c.m);*c.entered=true;c.s->notify_all();if(!c.s->wait_for(lock,std::chrono::seconds(2),[&](){return *c.allow;}))++*c.errors;return success();};
        // Test orchestration mutex only; no native lock/OSObject execution.
        std::thread reader([&](){GateScope hold(gate.access());if(g.consume(0,{&slow,callback}).ok())++accepted;else ++errors;});
        {std::unique_lock<std::mutex> lock(mutex);if(!signal.wait_for(lock,std::chrono::seconds(2),[&](){return entered;}))++errors;}
        std::atomic<bool> stopAttempted{false};
        std::thread closer([&](){stopAttempted=true;signal.notify_all();GateScope hold(gate.access());if(!g.stop().ok())++errors;});
        {std::unique_lock<std::mutex> lock(mutex);
            if(!signal.wait_for(lock,std::chrono::seconds(2),[&](){return stopAttempted.load();}))++errors;
            allowReturn=true;signal.notify_all();}reader.join();closer.join();
        auto attempts=[&](){for(unsigned i=0;i<80;++i){GateScope hold(gate.access());if(g.consume(0,{}).ok())++errors;else ++denied;if(!g.stop().ok())++errors;}};
        std::thread a(attempts),b(attempts);a.join();b.join();
        {GateScope hold(gate.access());check("scope_stop_serialization",accepted==1&&denied==160&&errors==0&&g.readyToFree()&&r.completes==1&&r.releases==1);}
        std::cout<<"M12_CONCURRENT scope=1 post_stop_attempts=160 errors="<<errors<<'\n';
    }
    std::cout<<"SUMMARY "<<pass<<' '<<fail<<'\n';return fail?1:0;
}
