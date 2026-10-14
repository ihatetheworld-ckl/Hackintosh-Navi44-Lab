// Host-only CPU mutex/reference mock, BSD-3-Clause. Never an IOKit object/lock.
#ifndef Navi44LifecycleMock_hpp
#define Navi44LifecycleMock_hpp
#include "../platform/lifecycle.hpp"
#include <array>
#include <mutex>
namespace NaviHost {
class ThreadGate {
    std::mutex mutex;
    inline static thread_local ThreadGate*current=nullptr;
    inline static thread_local bool interrupt=false;
    static bool enter(void*ctx){
        if(current||interrupt)return false;
        auto&g=*static_cast<ThreadGate*>(ctx);g.mutex.lock();current=&g;return true;
    }
    static void leave(void*ctx){
        auto&g=*static_cast<ThreadGate*>(ctx);if(current!=&g)return;
        current=nullptr;g.mutex.unlock();
    }
    static bool held(void*ctx){return current==ctx&&!interrupt;}
public:
    NaviPlatform::AccessOps access(){return {{this,enter,leave},held};}
    static void interruptContext(bool value){interrupt=value;}
};
class GateScope {
    NaviPlatform::ExecutionOps ops;bool acquired;
public:
    explicit GateScope(NaviPlatform::AccessOps access):ops(access.execution),acquired(ops.enter(ops.context)){}
    ~GateScope(){if(acquired)ops.leave(ops.context);}
    explicit operator bool()const{return acquired;}
    GateScope(const GateScope&)=delete;GateScope&operator=(const GateScope&)=delete;
};
struct ReferenceMock {
    std::array<uint8_t,4096>bytes{};
    int references{1};unsigned retains{0},releases{0},prepares{0},completes{0};
    bool failRetain{false},failView{false},failPrepare{false},failComplete{false},alive{true};
    NaviCore::View overrideView{};bool useOverride{false};
    void(*onRelease)(void*){nullptr};void*hook{nullptr};
    static bool retain(void*ctx){auto&r=*static_cast<ReferenceMock*>(ctx);if(r.failRetain||!r.alive)return false;++r.references;++r.retains;return true;}
    static void release(void*ctx){
        auto&r=*static_cast<ReferenceMock*>(ctx);++r.releases;--r.references;
        if(!r.references){r.alive=false;r.bytes.fill(0xdd);}
        if(r.onRelease)r.onRelease(r.hook);
    }
    static NaviCore::Result view(void*ctx,NaviCore::View&out){
        auto&r=*static_cast<ReferenceMock*>(ctx);out={};
        if(r.failView||!r.alive)return NaviCore::failure("mock_view_failure");
        out=r.useOverride?r.overrideView:NaviCore::View{r.bytes.data(),r.bytes.size()};return NaviCore::success();
    }
    static NaviCore::Result prepare(void*ctx){auto&r=*static_cast<ReferenceMock*>(ctx);++r.prepares;return r.failPrepare?NaviCore::failure("mock_prepare_failure"):NaviCore::success();}
    static NaviCore::Result complete(void*ctx){auto&r=*static_cast<ReferenceMock*>(ctx);++r.completes;return r.failComplete?NaviCore::failure("mock_complete_failure"):NaviCore::success();}
    NaviPlatform::ReferenceOps ops(){return {this,retain,release,view,prepare,complete};}
};
}
#endif
