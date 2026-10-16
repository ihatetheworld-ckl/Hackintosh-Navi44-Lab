// Genuine SDK type mismatch / forbidden initialization reference; never run.
#if defined(N44_ABI_MISMATCH)
#include <IOKit/IOLib.h>
static_assert(__is_same(decltype(&IOLog),bool(*)(const char*,...)),"deliberately wrong API ABI");
#elif defined(N44_ILLEGAL_INIT)
extern "C" int n44_hardware_initialization_requested();
int n44ForbiddenPath(){return n44_hardware_initialization_requested();}
#endif
