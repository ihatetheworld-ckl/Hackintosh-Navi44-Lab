// Genuine SDK26 layout only, never linked into the offline kext construction.
#include <IOKit/IOService.h>
class N44LayoutReference:public IOService {virtual void neverInstantiate()=0;public:bool init(OSDictionary*)override;};
bool N44LayoutReference::init(OSDictionary*){return false;}
extern "C" {
unsigned long n44_size_OSObject=sizeof(OSObject),n44_align_OSObject=alignof(OSObject);
unsigned long n44_size_OSMetaClass=sizeof(OSMetaClass),n44_align_OSMetaClass=alignof(OSMetaClass);
unsigned long n44_size_IORegistryEntry=sizeof(IORegistryEntry),n44_align_IORegistryEntry=alignof(IORegistryEntry);
unsigned long n44_size_IOService=sizeof(IOService),n44_align_IOService=alignof(IOService);
}
