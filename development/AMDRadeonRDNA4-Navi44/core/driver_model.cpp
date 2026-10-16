#include "driver_model.hpp"
namespace NaviModel {
using namespace NaviCore;
Result planDevice(const QueryCandidate&query,DevicePlan&out){
    out={};uint8_t wire[QueryCandidateSize]{};Result r=encodeQuery(query,wire,sizeof(wire));if(!r.ok())return r;
    QueryCandidate canonical{};r=decodeQuery({wire,sizeof(wire)},canonical);if(!r.ok())return r;
    if(canonical.device.profile.family!=Asic::Family::Navi44||canonical.device.profile.target!=Asic::Target::Gfx1200)
        return failure("driver_model_requires_navi44",Error::Unsupported);
    out.target=canonical.device.profile.target;out.generation=canonical.generation;out.metadataPresent=canonical.device.present;
    out.backend=Readiness::Unverified;
    return success(); // Candidate metadata accepted; no runtime readiness or capability.
}
Result planDisplay(const NaviDisplay::Mode&m,const NaviDisplay::Connector&connector,const NaviDisplay::LinkBudget&link,
    const NaviDisplay::EngineBudget&engine,uint8_t bpp,DisplayPlan&out){
    out={};if(connector.hardwareVerified||connector.routingKnown)return failure("routing_evidence_not_available",Error::Unsupported);
    if(connector.type==AtomBios::ConnectorUnknown)return failure("connector_unknown",Error::Missing);
    if(connector.type!=AtomBios::ConnectorDP&&connector.type!=AtomBios::ConnectorHDMIA)return failure("connector_model_unsupported",Error::Unsupported);
    if((connector.type==AtomBios::ConnectorDP&&link.kind!=NaviDisplay::LinkKind::Unknown&&link.kind!=NaviDisplay::LinkKind::Dp8b10b)||
       (connector.type==AtomBios::ConnectorHDMIA&&link.kind!=NaviDisplay::LinkKind::Unknown&&link.kind!=NaviDisplay::LinkKind::Tmds))
        return failure("connector_link_mismatch",Error::Mismatch);
    DisplayPlan result{};Result r=NaviDisplay::assess(m,link,engine,bpp,result.arithmetic);if(!r.ok())return r;
    result.routing=Readiness::Unverified;out=result;return success();
}
}
