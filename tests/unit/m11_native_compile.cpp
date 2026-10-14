// Abstract, uninstantiable IOService interface. No metaclass registration,
// provider matching, PCI, registerService, UserClient, IRQ, or hardware code.
#include "../../development/AMDRadeonRDNA4-Navi44/platform/darwin_owner_storage.hpp"
#include <IOKit/IOService.h>
#include <IOKit/IOLib.h>
#include <IOKit/IOBufferMemoryDescriptor.h>
#include <libkern/c++/OSData.h>
static_assert(__is_same(decltype(&IOMallocAligned),void*(*)(vm_size_t,vm_offset_t)),"allocator prototype");
static_assert(__is_same(decltype(&IOFreeAligned),void(*)(void*,vm_size_t)),"allocator release prototype");
static_assert(__is_same(decltype(&IOLog),void(*)(const char*,...)),"logger prototype");
static_assert(__is_same(decltype(&OSData::withBytes),OSData*(*)(const void*,unsigned int)),"raw OSData factory ABI");
static_assert(__is_same(decltype(&IOBufferMemoryDescriptor::withBytes),IOBufferMemoryDescriptor*(*)(const void*,vm_size_t,IODirection,bool)),"raw Buffer factory ABI");
static_assert(sizeof(vm_size_t)==8&&sizeof(vm_offset_t)==8&&sizeof(IOOptionBits)==4&&sizeof(IODirection)==4,"target integer widths");
class N44OfflineServiceContract:public IOService {
    // No constructible runtime class or OSDefineMetaClass registration.
    virtual void compileOnlyInterface()=0;
protected:
    // Final reference-count teardown only; not callable through our public probe.
    void free() override{IOService::free();}
public:
    bool init(OSDictionary*d=nullptr) override{return IOService::init(d);}
    bool start(IOService*) override{return false;} // offline binding always denied
    void stop(IOService*p) override{IOService::stop(p);}
    bool open(IOService*,IOOptionBits=0,void* =nullptr) override{return false;}
    void close(IOService*,IOOptionBits=0) override{}
    bool willTerminate(IOService*p,IOOptionBits o) override{return IOService::willTerminate(p,o);}
    bool didTerminate(IOService*p,IOOptionBits o,bool*defer) override{return IOService::didTerminate(p,o,defer);}
};
static_assert(__is_abstract(N44OfflineServiceContract),"no instantiable service");
static_assert(sizeof(NaviDarwin::NativeOwnerStorage)<65536,"long-lived owner allocation budget");
NaviCore::Result n44StorageCompile(NaviDarwin::NativeOwnerStorage&s,NaviCore::View v){return s.initialize(v,NaviDarwin::CpuSnapshotStorage::DataCopy);}
// Qualified calls force genuine superclass imports; none is called from an entry.
bool n44ServiceInitCompile(N44OfflineServiceContract&s,OSDictionary*d){return s.N44OfflineServiceContract::init(d);}
void n44ServiceCleanupCompile(N44OfflineServiceContract&s,IOService*p){s.N44OfflineServiceContract::stop(p);}
bool n44ServiceTerminationCompile(N44OfflineServiceContract&s,IOService*p,IOOptionBits o,bool*d){return s.N44OfflineServiceContract::willTerminate(p,o)&&s.N44OfflineServiceContract::didTerminate(p,o,d);}
