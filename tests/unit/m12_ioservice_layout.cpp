// Genuine current-SDK layout reference only. Excluded from the kernel link allowlist.
#include <IOKit/IOService.h>
class N44LayoutReference:public IOService {
    virtual void neverInstantiate()=0;
public:bool init(OSDictionary*)override;
};
bool N44LayoutReference::init(OSDictionary*){return false;}
extern "C" {
unsigned long n44_size_OSObject=sizeof(OSObject);
unsigned long n44_size_IORegistryEntry=sizeof(IORegistryEntry);
unsigned long n44_size_IOService=sizeof(IOService);
unsigned long n44_align_IOService=alignof(IOService);
}
