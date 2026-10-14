// Bounded actual behavior calibration against M9/current pure headers.
// No kernel/GPU calls. BSD-3-Clause.
#include "contract.hpp"
#include <iostream>
int main(){
    using namespace NaviPlatform;
    struct Memory {alignas(16) uint8_t bytes[32]{};Lease*lease{nullptr};unsigned releases{0};} memory;
    MemoryOps ops{&memory,[](void*ctx,size_t,size_t)->void*{return static_cast<Memory*>(ctx)->bytes;},
        [](void*ctx,void*,size_t){auto&m=*static_cast<Memory*>(ctx);++m.releases;if(m.releases==1)m.lease->close();}};
    Lease lease(ops);memory.lease=&lease;if(!lease.open(16,16))return 2;lease.close();
    const bool single=memory.releases==1;
    NodePool pool;auto scratch=pool.contract();NaviCore::Node foreign[1]{};
    auto*p=scratch.acquire(scratch.context,8);if(!p)return 2;
    scratch.release(scratch.context,foreign,8);
    const bool stillLocked=scratch.acquire(scratch.context,8)==nullptr;
    scratch.release(scratch.context,p,8);
    std::cout<<"LEASE_RELEASES "<<memory.releases<<" EXPECTED 1\n"
             <<"POOL_FOREIGN_RETURN_LOCKED "<<stillLocked<<" EXPECTED 1\n";
    return single&&stillLocked?0:1;
}
