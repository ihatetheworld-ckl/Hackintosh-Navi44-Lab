// M9: compiled as an x86_64 object with genuine Apple Kernel.framework headers.
// Compile evidence only: no kernel link, service binding or native execution.
// Actual IOKit interfaces only; no PCI/device/service/MMIO/DMA methods. BSD-3-Clause.
#include "darwin_native.hpp"
#include <IOKit/IOLib.h>
namespace NaviDarwin {
namespace {
void*allocate(void*,size_t bytes,size_t alignment){
    // Parsing scratch only. Must run in thread context, outside simple locks.
    if(!bytes||bytes>65536||!alignment||alignment>4096||(alignment&(alignment-1)))return nullptr;
    static_assert(sizeof(vm_size_t)>=sizeof(size_t),"check narrowing for target Kernel SDK");
    return IOMallocAligned(static_cast<vm_size_t>(bytes),static_cast<vm_offset_t>(alignment));
}
void release(void*,void*p,size_t bytes){if(p)IOFreeAligned(p,static_cast<vm_size_t>(bytes));}
void record(void*,NaviCore::Result r){
    // Only internal static diagnostic tokens. Do not log addresses or input payloads.
    IOLog("N44Core code=%u offset=%llu detail=%s\n",static_cast<unsigned>(r.code),
          static_cast<unsigned long long>(r.offset),r.detail?r.detail:"none");
}
}
NaviPlatform::MemoryOps nativeMemoryOps(){return {nullptr,allocate,release};}
NaviPlatform::LogOps nativeLogOps(){return {nullptr,record};}
NaviPlatform::ScratchOps nativeScratchOps(NaviPlatform::NodePool&pool){return pool.contract();}
IOReturn nativeError(NaviCore::Result r){
    using NaviCore::Error;
    switch(r.code){
        case Error::None:return kIOReturnSuccess;
        case Error::Budget:return kIOReturnNoMemory;
        case Error::Unsupported:return kIOReturnUnsupported;
        case Error::Missing:return kIOReturnNotFound;
        default:return kIOReturnBadArgument;
    }
}
}
