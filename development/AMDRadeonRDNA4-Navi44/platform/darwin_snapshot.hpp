// Genuine Apple API adapter, compile/partial-link only. BSD-3-Clause.
#ifndef Navi44DarwinSnapshot_hpp
#define Navi44DarwinSnapshot_hpp
#if !defined(__APPLE__) || !defined(KERNEL)
#error Genuine separately authorized kernel object build required
#endif
#include "lifecycle.hpp"
#include <libkern/c++/OSObject.h>
namespace NaviDarwin {
enum class CpuSnapshotStorage:uint8_t { DataCopy,BufferCopy };
// Caller owns long-lived wrapper/gate storage. No IOService/UserClient/GPU entry.
// Close/return all leases under gate and require readyToFree before freeing it.
class NativeSnapshot {
    NaviPlatform::SnapshotOwner owner_;
    OSObject*object_{nullptr};CpuSnapshotStorage kind_{CpuSnapshotStorage::DataCopy};
    static bool retain(void*);static void release(void*);
    static NaviCore::Result view(void*,NaviCore::View&);
public:
    NativeSnapshot(NaviPlatform::AccessOps access,uint64_t generation):owner_(access,generation){}
    NativeSnapshot(const NativeSnapshot&)=delete;NativeSnapshot&operator=(const NativeSnapshot&)=delete;
    NaviCore::Result createCopy(NaviCore::View,CpuSnapshotStorage);
    NaviPlatform::SnapshotOwner&owner(){return owner_;}
};
}
#endif
