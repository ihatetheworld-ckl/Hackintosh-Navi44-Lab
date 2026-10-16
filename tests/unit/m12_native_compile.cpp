// No provider matching, service registration, hardware access or native execution.
#include "../../development/AMDRadeonRDNA4-Navi44/platform/darwin_gate.hpp"
#include "../../development/AMDRadeonRDNA4-Navi44/platform/darwin_owner_storage.hpp"
static_assert(sizeof(NaviPlatform::ScopedInput)<128,"scope is small metadata");
static_assert(sizeof(NaviDarwin::NativeOwnerStorage)<65536,"long-lived external storage");
static_assert(__is_same(decltype(&IORecursiveLockLock),void(*)(IORecursiveLock*)),"kernel lock ABI");
static_assert(__is_same(decltype(&IORecursiveLockUnlock),void(*)(IORecursiveLock*)),"kernel unlock ABI");
static_assert(__is_same(decltype(&IORecursiveLockHaveLock),boolean_t(*)(const IORecursiveLock*)),"current-thread lock ownership ABI");
static_assert(__is_same(decltype(&ml_at_interrupt_context),boolean_t(*)()),"interrupt context ABI");
static_assert(__is_same(decltype(&ml_get_interrupts_enabled),boolean_t(*)()),"interrupt enable ABI");
NaviPlatform::AccessOps n44KernelGateCompile(NaviDarwin::BorrowedKernelGate&g){return g.access();}
namespace {
// Type-checked lifecycle integration, never called from a kmod entry or Host.
struct NativeGateCall {
    NaviPlatform::ExecutionOps ops;bool entered;
    explicit NativeGateCall(NaviDarwin::BorrowedKernelGate&g):ops(g.access().execution),entered(ops.enter(ops.context)){}
    ~NativeGateCall(){if(entered)ops.leave(ops.context);}
    NativeGateCall(const NativeGateCall&)=delete;
};
}
NaviCore::Result n44ScopedNativeCompile(NaviDarwin::NativeOwnerStorage&s,NaviDarwin::BorrowedKernelGate&g,NaviPlatform::InputConsumer c){
    NativeGateCall hold{g};return hold.entered?s.consume(c):NaviCore::failure("native_gate_context");
}
NaviCore::Result n44StopDrainNativeCompile(NaviDarwin::NativeOwnerStorage&s,NaviDarwin::BorrowedKernelGate&g){
    NativeGateCall hold{g};return hold.entered?s.stop():NaviCore::failure("native_gate_context");
}
