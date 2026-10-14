// Object code only: none of these kernel calls is executed by Host tests.
#include "darwin_snapshot.hpp"
#include <libkern/c++/OSData.h>
#include <IOKit/IOBufferMemoryDescriptor.h>
namespace NaviDarwin {
using namespace NaviCore;
// Public SDK defaults to raw OSPtr, not experimental OSSharedPtr factories.
static_assert(__is_same(OSPtr<OSData>,OSData*),"use the audited public raw factory ABI");
static_assert(sizeof(size_t)>=sizeof(IOByteCount),"descriptor length must not narrow");
bool NativeSnapshot::retain(void*ctx){
    auto&s=*static_cast<NativeSnapshot*>(ctx);if(!s.object_)return false;
    s.object_->retain();return true;
}
void NativeSnapshot::release(void*ctx){
    auto&s=*static_cast<NativeSnapshot*>(ctx);OSObject*p=s.object_;s.object_=nullptr;
    if(p)p->release();
}
Result NativeSnapshot::view(void*ctx,View&out){
    auto&s=*static_cast<NativeSnapshot*>(ctx);out={};
    if(!s.object_)return failure("native_snapshot_missing",Error::Missing);
    if(s.kind_==CpuSnapshotStorage::DataCopy){
        const auto*data=static_cast<const OSData*>(s.object_);
        out={static_cast<const uint8_t*>(data->getBytesNoCopy()),data->getLength()};
    }else{
        auto*buffer=static_cast<IOBufferMemoryDescriptor*>(s.object_);
        out={static_cast<const uint8_t*>(buffer->getBytesNoCopy()),static_cast<size_t>(buffer->getLength())};
    }
    return success();
}
Result NativeSnapshot::createCopy(View input,CpuSnapshotStorage kind){
    NaviPlatform::OwnerState state{};size_t leases=0;
    Result r=owner_.inspect(state,leases);if(!r.ok())return r;
    if(state!=NaviPlatform::OwnerState::Created||object_)return failure("native_snapshot_state",Error::Protocol);
    const uintptr_t address=reinterpret_cast<uintptr_t>(input.data);
    if(!input.data||!input.size||input.size>NaviPlatform::SnapshotOwner::MaxBytes||input.size-1>UINTPTR_MAX-address)
        return failure("native_snapshot_bounds",Error::Bounds);
    kind_=kind;NaviPlatform::ReferenceOps ref{this,retain,release,view,nullptr,nullptr};
    if(kind==CpuSnapshotStorage::DataCopy){
        static_assert(NaviPlatform::SnapshotOwner::MaxBytes<=UINT32_MAX,"OSData length narrowing");
        auto data=OSData::withBytes(input.data,static_cast<unsigned int>(input.size));
        if(!data)return failure("native_data_allocation",Error::Budget);
        object_=data;r=owner_.activate(ref);
        // The public raw factory returns reference count 1. Drop that initial
        // reference after activate retained its own, including failure cleanup.
        data->release();if(!r.ok())object_=nullptr;return r;
    }
    if(kind==CpuSnapshotStorage::BufferCopy){
        auto buffer=IOBufferMemoryDescriptor::withBytes(input.data,static_cast<vm_size_t>(input.size),kIODirectionNone);
        if(!buffer)return failure("native_buffer_allocation",Error::Budget);
        object_=buffer;r=owner_.activate(ref);buffer->release();if(!r.ok())object_=nullptr;return r;
    }
    return failure("native_snapshot_storage",Error::Unsupported);
}
}
