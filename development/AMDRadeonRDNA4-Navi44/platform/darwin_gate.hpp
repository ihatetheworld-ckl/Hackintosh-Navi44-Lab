// Genuine borrowed kernel lock adapter. BSD-3-Clause. Compile only in this lab.
// The publisher owns lock/adapter storage, removes every callback source and
// drains all waiters before destroying either. This adapter never frees a lock.
#ifndef Navi44DarwinGate_hpp
#define Navi44DarwinGate_hpp
#if !defined(__APPLE__) || !defined(KERNEL)
#error Genuine Apple Kernel build required
#endif
#include "lifecycle.hpp"
#include <IOKit/IOLocks.h>
namespace NaviDarwin {
class BorrowedKernelGate {
    IORecursiveLock*const lock_;
    static bool ordinary();static bool enter(void*);static void leave(void*);static bool held(void*);
public:
    explicit BorrowedKernelGate(IORecursiveLock*lock):lock_(lock){}
    BorrowedKernelGate(const BorrowedKernelGate&)=delete;BorrowedKernelGate&operator=(const BorrowedKernelGate&)=delete;
    NaviPlatform::AccessOps access(){return {{this,enter,leave},held};}
};
}
#endif
