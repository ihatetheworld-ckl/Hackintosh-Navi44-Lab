// Pure CPU platform contract; no PCI/MMIO/IOKit entry points. BSD-3-Clause.
#ifndef Navi44PlatformContract_hpp
#define Navi44PlatformContract_hpp
#include "../core/validation.hpp"
namespace NaviPlatform {
struct MemoryOps {
    void*context;
    void*(*allocate)(void*,size_t,size_t);
    void(*release)(void*,void*,size_t);
};
struct LogOps { void*context;void(*record)(void*,NaviCore::Result); };
enum class SnapshotKind:uint8_t { DiscoveryFile, ElfFile, FirmwareFile };
struct SnapshotOps {
    void*context;NaviCore::Result(*borrow)(void*,SnapshotKind,NaviCore::View&);
    void(*release)(void*,NaviCore::View){nullptr};
};
// The allocator must supply live Node objects, not raw bytes cast to Node*.
struct ScratchOps {
    void*context{nullptr};NaviCore::Node*(*acquire)(void*,size_t){nullptr};
    void(*release)(void*,NaviCore::Node*,size_t){nullptr};
};
// Adapter establishes thread context and serialization. No lock primitives here.
struct ExecutionOps {
    void*context{nullptr};bool(*enter)(void*){nullptr};void(*leave)(void*){nullptr};
};
struct Contract { MemoryOps memory;LogOps log;SnapshotOps snapshots;ScratchOps scratch{};ExecutionOps execution{}; };
class NodePool {
    NaviCore::Node nodes[512]{};bool busy{false};
    static NaviCore::Node*acquire(void*ctx,size_t count){
        auto&p=*static_cast<NodePool*>(ctx);if(p.busy||!count||count>512)return nullptr;
        p.busy=true;return p.nodes;
    }
    static void release(void*ctx,NaviCore::Node*,size_t){static_cast<NodePool*>(ctx)->busy=false;}
public:
    NodePool()=default;NodePool(const NodePool&)=delete;NodePool&operator=(const NodePool&)=delete;
    ScratchOps contract(){return {this,acquire,release};}
};
// NodePool is not internally synchronized. Owner constructs it outside the
// kernel stack and supplies ExecutionOps for thread-context serialized access.
class Lease {
    MemoryOps ops;void*pointer{nullptr};size_t bytes{0};
public:
    explicit Lease(MemoryOps m):ops(m){}
    Lease(const Lease&)=delete;Lease&operator=(const Lease&)=delete;
    ~Lease(){close();}
    bool open(size_t n,size_t alignment){
        if(pointer||!n||!alignment||(alignment&(alignment-1))||!ops.allocate||!ops.release)return false;
        void*p=ops.allocate(ops.context,n,alignment);if(!p)return false;
        if(reinterpret_cast<uintptr_t>(p)%alignment){ops.release(ops.context,p,n);return false;}
        pointer=p;bytes=n;return true;
    }
    void close(){if(pointer){ops.release(ops.context,pointer,bytes);pointer=nullptr;bytes=0;}}
    void*data()const{return pointer;}
    NaviCore::View view()const{return {static_cast<const uint8_t*>(pointer),bytes};}
};
inline NaviCore::Result validateSnapshot(Contract c,Asic::Target target){
    using namespace NaviCore;Result r=failure("platform_context_unverified",Error::Protocol);
    if(!c.execution.enter||!c.execution.leave||!c.execution.enter(c.execution.context)){
        // No callback (including log) is safe until execution context is held.
        return r;
    }
    struct Call {ExecutionOps ops;~Call(){ops.leave(ops.context);}} call{c.execution};
    View input{nullptr,0};
    if(!c.snapshots.borrow||!c.snapshots.release)r=failure("snapshot_unavailable",Error::Missing);
    else r=c.snapshots.borrow(c.snapshots.context,SnapshotKind::ElfFile,input);
    if(r.ok()){
        struct Input {SnapshotOps ops;View v;~Input(){ops.release(ops.context,v);}} lease{c.snapshots,input};
        Node*nodes=nullptr;
        if(c.scratch.acquire&&c.scratch.release)nodes=c.scratch.acquire(c.scratch.context,512);
        if(!nodes)r=failure("platform_allocation_failed",Error::Budget);
        else {
            struct Arena {ScratchOps ops;Node*p;~Arena(){ops.release(ops.context,p,512);}} owned{c.scratch,nodes};
            Scratch arena{nodes,512,0};r=elf(input,target,arena);
        }
    }
    if(c.log.record)c.log.record(c.log.context,r);return r;
}
}
#endif
