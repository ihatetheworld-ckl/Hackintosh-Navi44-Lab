// CPU-only address/fence ledger. No VRAM allocation, GPU VA mapping or submit.
// BSD-3-Clause. Caller holds the same gate and long-lived GenerationClock.
#ifndef Navi44ResourceModel_hpp
#define Navi44ResourceModel_hpp
#include "shutdown.hpp"
namespace NaviModel {
class ResourceModel;
struct ModelHandle {const ResourceModel*owner{nullptr};uint64_t generation{0};size_t slot{0};};
struct ModelFence {ModelHandle buffer{};uint64_t serial{0};};
enum class FenceState:uint8_t { Idle,Pending,Completed,TimedOut,Revoked };
struct ResourceInfo {uint64_t base{0},bytes{0};FenceState fence{FenceState::Idle};bool revoked{false};};
class ResourceModel {
    NaviPlatform::AccessOps access_;NaviPlatform::GenerationClock&clock_;uint64_t base_,bytes_,budget_,used_{0};bool stopped_{false};
    struct Entry {uint64_t generation{0},base{0},bytes{0},serial{0},deadline{0};FenceState fence{FenceState::Idle};bool revoked{false};} entries_[8]{};
    bool held()const;bool valid(const ModelHandle&)const;
public:
    // 4096 is a CPU simulation page unit, not a discovered GPU page size.
    ResourceModel(NaviPlatform::AccessOps a,NaviPlatform::GenerationClock&c,uint64_t base,uint64_t bytes,uint64_t budget):access_(a),clock_(c),base_(base),bytes_(bytes),budget_(budget){}
    ResourceModel(const ResourceModel&)=delete;ResourceModel&operator=(const ResourceModel&)=delete;
    NaviCore::Result reserve(uint64_t,uint64_t,ModelHandle&);
    NaviCore::Result queueModel(const ModelHandle&,uint64_t now,uint64_t deadline,ModelFence&);
    NaviCore::Result completeModel(const ModelFence&);
    NaviCore::Result acknowledgeCancellationModel(const ModelFence&);
    NaviCore::Result expireModel(uint64_t now);
    NaviCore::Result inspect(const ModelHandle&,ResourceInfo&)const;
    NaviCore::Result release(ModelHandle&);
    NaviCore::Result stop();NaviCore::Result resetModel();
    bool readyToFree()const;bool hardwareSubmissionAllowed()const{return false;}
};
}
#endif
