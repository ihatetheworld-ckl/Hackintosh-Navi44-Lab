// Native owner storage is caller-owned, never placed on the kernel stack.
// BSD-3-Clause. Only compile/link checks; no API execution in Host tests.
#ifndef Navi44DarwinOwnerStorage_hpp
#define Navi44DarwinOwnerStorage_hpp
#include "darwin_snapshot.hpp"
#include "shutdown.hpp"
namespace NaviDarwin {
class NativeOwnerStorage {
    NativeSnapshot snapshot_;NaviPlatform::ShutdownBarrier barrier_;NaviPlatform::NodePool scratch_;
    static NaviCore::Node*acquire(void*ctx,size_t count){
        auto&s=*static_cast<NativeOwnerStorage*>(ctx);NaviPlatform::ShutdownState state{};size_t n=0;unsigned f=0;
        if(!s.barrier_.inspect(state,n,f).ok()||state!=NaviPlatform::ShutdownState::Active)return nullptr;
        auto ops=s.scratch_.contract();return ops.acquire(ops.context,count);
    }
    static void release(void*ctx,NaviCore::Node*p,size_t count){
        auto&s=*static_cast<NativeOwnerStorage*>(ctx);NaviPlatform::ShutdownState state{};size_t n=0;unsigned f=0;
        if(!s.barrier_.inspect(state,n,f).ok())return;
        auto ops=s.scratch_.contract();ops.release(ops.context,p,count);
    }
public:
    // Generation must come from the long-lived, serialized GenerationClock.
    NativeOwnerStorage(NaviPlatform::AccessOps access,uint64_t generation):snapshot_(access,generation),barrier_(access){}
    NativeOwnerStorage(const NativeOwnerStorage&)=delete;NativeOwnerStorage&operator=(const NativeOwnerStorage&)=delete;
    NaviCore::Result initialize(NaviCore::View view,CpuSnapshotStorage kind){
        auto r=barrier_.bind(snapshot_.owner());if(!r.ok())return r;
        r=snapshot_.createCopy(view,kind);if(!r.ok()){barrier_.stop();return r;}
        return barrier_.start();
    }
    NaviPlatform::ShutdownBarrier&lifetime(){return barrier_;}
    NaviPlatform::ScratchOps scratch(){return {this,acquire,release};}
    // Caller may destroy storage only under gate when this is true.
    bool readyToFree()const{return barrier_.readyToFree()&&scratch_.idle();}
};
}
#endif
