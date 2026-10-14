// Host Mock uses a fixed caller-owned CPU array, never a device or allocator API.
#ifndef Navi44HostPlatformMock_hpp
#define Navi44HostPlatformMock_hpp
#include "../platform/contract.hpp"
namespace NaviHost {
struct PlatformMock {
    NaviCore::Node arena[512]{};
    NaviCore::View snapshot{nullptr,0};
    unsigned allocations{0},releases{0},logs{0},borrows{0},returns{0},enters{0},leaves{0};
    bool busy{false},deny{false},inCall{false},wrongContext{false};
    static void*allocate(void*ctx,size_t n,size_t alignment){
        auto&m=*static_cast<PlatformMock*>(ctx);
        if(m.deny||m.busy||n>sizeof(m.arena)||alignment>alignof(NaviCore::Node))return nullptr;
        m.busy=true;++m.allocations;return m.arena;
    }
    static void release(void*ctx,void*,size_t){auto&m=*static_cast<PlatformMock*>(ctx);m.busy=false;++m.releases;}
    static void log(void*ctx,NaviCore::Result){++static_cast<PlatformMock*>(ctx)->logs;}
    static NaviCore::Result borrow(void*ctx,NaviPlatform::SnapshotKind,NaviCore::View&out){
        auto&m=*static_cast<PlatformMock*>(ctx);out=m.snapshot;
        if(!out.data)return NaviCore::failure("snapshot_unavailable",NaviCore::Error::Missing);
        ++m.borrows;return NaviCore::success();
    }
    static void giveBack(void*ctx,NaviCore::View){++static_cast<PlatformMock*>(ctx)->returns;}
    static NaviCore::Node*nodes(void*ctx,size_t count){
        if(!count||count>512)return nullptr;
        return static_cast<NaviCore::Node*>(allocate(ctx,count*sizeof(NaviCore::Node),alignof(NaviCore::Node)));
    }
    static void returnNodes(void*ctx,NaviCore::Node*p,size_t count){release(ctx,p,count*sizeof(NaviCore::Node));}
    static bool enter(void*ctx){
        auto&m=*static_cast<PlatformMock*>(ctx);if(m.inCall||m.wrongContext)return false;
        m.inCall=true;++m.enters;return true;
    }
    static void leave(void*ctx){auto&m=*static_cast<PlatformMock*>(ctx);m.inCall=false;++m.leaves;}
    NaviPlatform::Contract contract(){
        return {{this,allocate,release},{this,log},{this,borrow,giveBack},
                {this,nodes,returnNodes},{this,enter,leave}};
    }
};
}
#endif
