// Caller-serialized shutdown over existing SnapshotOwner; BSD-3-Clause.
#ifndef Navi44Shutdown_hpp
#define Navi44Shutdown_hpp
#include "lifecycle.hpp"
namespace NaviPlatform {
// One long-lived issuer per ownership domain, under its exact gate. Never reset
// or recreate it while stale tickets can exist. Address identity alone is not ABA-safe.
class GenerationClock {
    AccessOps access_;uint64_t next_;
public:
    explicit GenerationClock(AccessOps access,uint64_t first=1):access_(access),next_(first){}
    GenerationClock(const GenerationClock&)=delete;GenerationClock&operator=(const GenerationClock&)=delete;
    NaviCore::Result issue(uint64_t&);
};
enum class ShutdownState:uint8_t { Created,Active,Stopping,Draining,Failed,Released };
class ShutdownBarrier {
    AccessOps access_;SnapshotOwner*owners_[8]{};size_t count_{0};
    ShutdownState state_{ShutdownState::Created};bool operation_{false};unsigned failures_{0};
    bool held()const;bool begin();void end(){operation_=false;}
    NaviCore::Result drainHeld();
public:
    static constexpr unsigned MaxCleanupFailures=4;
    explicit ShutdownBarrier(AccessOps access):access_(access){}
    ShutdownBarrier(const ShutdownBarrier&)=delete;ShutdownBarrier&operator=(const ShutdownBarrier&)=delete;
    // Owner storage and gate must outlive this barrier and every outstanding ticket.
    NaviCore::Result bind(SnapshotOwner&);NaviCore::Result start();
    NaviCore::Result borrow(size_t,SnapshotTicket&);NaviCore::Result read(size_t,const SnapshotTicket&,NaviCore::View&);
    NaviCore::Result giveBack(size_t,SnapshotTicket&);
    NaviCore::Result stop();NaviCore::Result poll();
    bool readyToFree()const;
    NaviCore::Result inspect(ShutdownState&,size_t&,unsigned&)const;
};
}
#endif
