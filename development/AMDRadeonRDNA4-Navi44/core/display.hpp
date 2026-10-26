// CPU-only display data. BSD-3-Clause; no renderer, transport or hardware access.
#ifndef Navi44DisplayCore_hpp
#define Navi44DisplayCore_hpp
#include "validation.hpp"
#include "../src/edid.hpp"
#include "../src/atombios.hpp"
namespace NaviDisplay {
using NaviCore::View;using NaviCore::Result;
enum class Origin:uint8_t { Unknown,Synthetic,StaticReference };
enum class ExtensionPolicy:uint8_t { RejectUnknown,KnownBlocksOnly,AllowDisplayId };
enum Source:uint32_t { BaseDtd=1,CtaDtd=2,Established=4,Standard=8,CtaVic=16,DisplayIdType1=32 };
struct Fraction {uint64_t numerator,denominator;};
struct Mode {
    Edid::DetailedTiming timing{};Fraction refresh{};uint32_t sources{0};
    bool sinkDeclared{false},hardwareVerified{false},sameRateAlternative{false};
};
struct Monitor {
    char manufacturer[4]{};uint16_t product{0};uint8_t revision{0};
    bool digital{false},partial{false},scdcAdvertised{false};Origin origin{Origin::Unknown};
    uint32_t sinkMaxTmdsKHz{0};size_t modeCount{0},duplicates{0},unresolvedTimings{0};
};
constexpr size_t MaxModes=64;
Result timing(const Edid::DetailedTiming&,Mode&);
// Caller owns storage (capacity 1..64); exact declared EDID length, maximum 4 blocks.
Result edid(View,Origin,Monitor&,Mode*storage,size_t capacity,
            ExtensionPolicy=ExtensionPolicy::RejectUnknown);
struct Connector {
    AtomBios::DisplayPath path{};AtomBios::PathRecords records{};
    AtomBios::ConnectorType type{AtomBios::ConnectorUnknown};
    bool hardwareVerified{false},routingKnown{false};
};
struct ConnectorList {
    Connector entries[AtomBios::MaxDisplayPaths]{};size_t count{0};
    Origin origin{Origin::Unknown};bool boardVerified{false};
};
Result connectors(View,Origin,ConnectorList&);
struct BoardDiagnostics {
    uint16_t subsysVid{0},subsysId{0};
    bool hasFirmwareInfo{false};
    AtomBios::FirmwareInfo3 firmware{};
    size_t gpioPinCount{0};
    AtomBios::GpioPin gpioPins[AtomBios::MaxGpioPins]{};
    Origin origin{Origin::Unknown};bool hardwareVerified{false};
};
Result boardDiagnostics(View,Origin,BoardDiagnostics&);
enum class LinkKind:uint8_t { Unknown,Dp8b10b,Tmds };
struct LinkBudget {
    Origin origin{Origin::Unknown};LinkKind kind{LinkKind::Unknown};
    uint8_t lanes{0};uint32_t rateMbps{0},tmdsClockKHz{0};
};
struct EngineBudget {Origin origin{Origin::Unknown};uint32_t maxPixelClockKHz{0};};
enum class Fit:uint8_t { Unknown,WithinBudget,Insufficient };
struct Decision {
    uint64_t requiredBitsPerSecond{0},linkPayloadBitsPerSecond{0},frameBytes{0},fullFrameBytesPerSecond{0};
    Fit link{Fit::Unknown},engine{Fit::Unknown};
    bool hardwareVerified{false},outputAllowed{false};
};
// Arithmetic preflight only; even WithinBudget cannot authorize output.
Result assess(const Mode&,const LinkBudget&,const EngineBudget&,uint8_t bitsPerPixel,Decision&);
}
#endif
