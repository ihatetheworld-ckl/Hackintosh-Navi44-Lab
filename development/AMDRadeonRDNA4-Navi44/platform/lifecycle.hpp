// Serialized CPU resource ownership; BSD-3-Clause. No hardware or OS types.
#ifndef Navi44Lifecycle_hpp
#define Navi44Lifecycle_hpp
#include "contract.hpp"
namespace NaviPlatform {
// Every operation requires this exact execution gate, already held by a thread.
// Gate implementation owns synchronization; isHeld must validate current thread.
struct AccessOps { ExecutionOps execution;bool(*isHeld)(void*){nullptr}; };
struct ReferenceOps {
    void*context{nullptr};bool(*retain)(void*){nullptr};void(*release)(void*){nullptr};
    NaviCore::Result(*view)(void*,NaviCore::View&){nullptr};
    NaviCore::Result(*prepare)(void*){nullptr};NaviCore::Result(*complete)(void*){nullptr};
};
enum class OwnerState:uint8_t { Created,Active,Closing,Revoked,Failed,Released };
class SnapshotOwner;
// No raw View accessor, copying, moving, or external destruction. Consumers may
// copy bounded bytes only while the owner holds its execution gate/callback.
// A malicious consumer can still stash a reference; use after callback is illegal.
class ScopedInput {
    NaviCore::View view_;const SnapshotOwner&owner_;
    ScopedInput(NaviCore::View v,const SnapshotOwner&o):view_(v),owner_(o){}
    ~ScopedInput()=default;friend class SnapshotOwner;
public:
    ScopedInput(const ScopedInput&)=delete;ScopedInput&operator=(const ScopedInput&)=delete;
    ScopedInput(ScopedInput&&)=delete;ScopedInput&operator=(ScopedInput&&)=delete;
    NaviCore::Result length(size_t&)const;
    NaviCore::Result copy(size_t offset,uint8_t*destination,size_t bytes)const;
    NaviCore::Result byte(size_t offset,uint8_t&)const;
};
struct InputConsumer {void*context{nullptr};NaviCore::Result(*consume)(void*,const ScopedInput&)noexcept{nullptr};};
// Identity binds obligations to their live owner as well as its generation.
// This is an in-process lifetime token, never an authorization credential.
struct SnapshotTicket { uint64_t owner{0},serial{0};size_t slot{0};const SnapshotOwner*identity{nullptr}; };
class SnapshotOwner {
public:
    static constexpr size_t MaxLeases=8,MaxBytes=1u<<20;
    // generation must be unique for this storage lifetime, including address reuse.
    SnapshotOwner(AccessOps access,uint64_t generation,SnapshotKind kind=SnapshotKind::ElfFile)
        : access_(access),generation_(generation),kind_(kind){}
    SnapshotOwner(const SnapshotOwner&)=delete;SnapshotOwner&operator=(const SnapshotOwner&)=delete;
    // Storage must outlive all tickets and be freed only after readyToFree().
    // No destructor attempts unsafe teardown without the caller's gate/context.
    NaviCore::Result activate(ReferenceOps,bool needsPreparation=false);
    NaviCore::Result borrow(SnapshotTicket&);
    NaviCore::Result read(const SnapshotTicket&,NaviCore::View&);
    NaviCore::Result giveBack(SnapshotTicket&);
    NaviCore::Result withInput(const SnapshotTicket&,InputConsumer);
    // Automatic ticket acquisition/return, including consumer error paths.
    NaviCore::Result consume(InputConsumer);
    NaviCore::Result close();NaviCore::Result revoke();
    bool readyToFree()const;
    NaviCore::Result inspect(OwnerState&,size_t&)const;
    SnapshotOps snapshots(){return {this,legacyBorrow,legacyRelease};}
    ExecutionOps execution()const{return access_.execution;}
private:
    friend class ScopedInput;
    AccessOps access_;uint64_t generation_,next_{1};SnapshotKind kind_;
    ReferenceOps reference_{};NaviCore::View input_{};
    uint64_t slots_[MaxLeases]{};size_t leases_{0};OwnerState state_{OwnerState::Created};
    bool retained_{false},prepared_{false},operation_{false},legacy_{false};
    SnapshotTicket legacyTicket_{};NaviCore::View legacyView_{};
    bool held()const;
    struct Call {
        SnapshotOwner&owner;bool entered;
        explicit Call(SnapshotOwner&);~Call();
    };
    bool valid(const SnapshotTicket&)const;
    NaviCore::Result borrowHeld(SnapshotTicket&);
    NaviCore::Result readHeld(const SnapshotTicket&,NaviCore::View&)const;
    NaviCore::Result returnHeld(SnapshotTicket&);
    NaviCore::Result finish();NaviCore::Result stop(OwnerState);
    NaviCore::Result fail(NaviCore::Result);
    static NaviCore::Result legacyBorrow(void*,SnapshotKind,NaviCore::View&);
    static void legacyRelease(void*,NaviCore::View);
};
}
#endif
