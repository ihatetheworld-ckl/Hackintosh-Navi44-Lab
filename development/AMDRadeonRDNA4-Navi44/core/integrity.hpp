// Explicit offline checksum convention; not authentication or AMD firmware loading.
#ifndef Navi44Integrity_hpp
#define Navi44Integrity_hpp
#include "validation.hpp"
namespace NaviCore {
enum class CrcConvention:uint8_t { Unknown,IsoHdlc };
struct Integrity {uint32_t computed;bool checksumMatched;bool signatureVerified;bool loadable;};
Result payloadChecksum(View,uint32_t expected,CrcConvention,Integrity&);
}
#endif
