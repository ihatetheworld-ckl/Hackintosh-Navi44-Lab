#include "darwin_gate.hpp"
namespace NaviDarwin {
bool BorrowedKernelGate::ordinary(){return !ml_at_interrupt_context()&&ml_get_interrupts_enabled();}
bool BorrowedKernelGate::enter(void*ctx){
    auto&g=*static_cast<BorrowedKernelGate*>(ctx);
    if(!g.lock_||!ordinary()||IORecursiveLockHaveLock(g.lock_))return false;
    // Caller must also guarantee a sleepable context with no spin lock held.
    IORecursiveLockLock(g.lock_);return true;
}
void BorrowedKernelGate::leave(void*ctx){
    auto&g=*static_cast<BorrowedKernelGate*>(ctx);
    if(g.lock_&&ordinary()&&IORecursiveLockHaveLock(g.lock_))IORecursiveLockUnlock(g.lock_);
}
bool BorrowedKernelGate::held(void*ctx){
    auto&g=*static_cast<BorrowedKernelGate*>(ctx);
    return g.lock_&&ordinary()&&IORecursiveLockHaveLock(g.lock_);
}
}
