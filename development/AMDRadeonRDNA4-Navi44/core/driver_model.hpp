// Navi44 static integration preflight; BSD-3-Clause. No GPU backend.
#ifndef Navi44DriverModel_hpp
#define Navi44DriverModel_hpp
#include "query_candidate.hpp"
#include "display.hpp"
namespace NaviModel {
enum class Readiness:uint8_t { Missing,Unverified,Unsupported };
struct DevicePlan {
    Asic::Target target{Asic::Target::Unknown};uint64_t generation{0};uint32_t metadataPresent{0};
    Readiness backend{Readiness::Missing};bool hardwareAllowed{false},displayAllowed{false},shaderAllowed{false};
};
NaviCore::Result planDevice(const NaviCore::QueryCandidate&,DevicePlan&);
struct DisplayPlan {
    NaviDisplay::Decision arithmetic{};Readiness routing{Readiness::Missing};
    bool trainingAllowed{false},scanoutAllowed{false};
};
NaviCore::Result planDisplay(const NaviDisplay::Mode&,const NaviDisplay::Connector&,
    const NaviDisplay::LinkBudget&,const NaviDisplay::EngineBudget&,uint8_t,DisplayPlan&);
}
#endif
