// Bounded DisplayID container metadata, not timing/scanout support. BSD-3-Clause.
// Format reference: Linux 24a19b953e2a3d0ea5a8c4951a0ab8f32720c907,
// drivers/gpu/drm/drm_displayid.c and drm_displayid_internal.h (MIT).
#ifndef Navi44DisplayId_hpp
#define Navi44DisplayId_hpp
#include "validation.hpp"
namespace NaviDisplay {
struct DisplayIdBlock {uint8_t tag{0},revision{0},bytes{0};uint16_t offset{0};};
struct DisplayIdSection {
    uint8_t version{0},primaryUse{0};size_t count{0};DisplayIdBlock blocks[32]{};
    bool timingDecoded{false},hardwareVerified{false},outputAllowed{false};
};
// One EDID extension, both checksum layers required; continuation unsupported.
// Opaque block inventory only. Success is structural validity, not semantics.
NaviCore::Result displayIdSection(NaviCore::View,DisplayIdSection&);
}
#endif
