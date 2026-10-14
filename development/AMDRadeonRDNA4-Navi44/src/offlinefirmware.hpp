// CPU-only common-header checks. BSD-3-Clause, see LICENSE.
#ifndef Navi44OfflineFirmware_hpp
#define Navi44OfflineFirmware_hpp
#include <stddef.h>
#include <stdint.h>
namespace OfflineFirmware {
enum class Error { None, Missing, HeaderVersion, Length, IpMismatch, CrcUnverified };
struct Need { uint16_t ipMajor, ipMinor; const char *component; };
inline uint16_t le16(const uint8_t *p) { return uint16_t(p[0]) | uint16_t(p[1]) << 8; }
inline uint32_t le32(const uint8_t *p) {
    return uint32_t(p[0]) | uint32_t(p[1]) << 8 | uint32_t(p[2]) << 16 | uint32_t(p[3]) << 24;
}
inline Error validate(const uint8_t *d, size_t n, const Need &need) {
    if (!d || n < 32) return Error::Missing;
    if (le16(d + 8) != 1 || le16(d + 10) != 0) return Error::HeaderVersion;
    const uint32_t size = le32(d), header = le32(d + 4);
    const uint32_t count = le32(d + 20), off = le32(d + 24);
    if (size != n || header < 32 || header > n || off < header || off > n ||
        !count || count > n - off) return Error::Length;
    if (le16(d + 12) != need.ipMajor || le16(d + 14) != need.ipMinor) return Error::IpMismatch;
    if (le32(d + 28)) return Error::CrcUnverified;
    // Structural validation only. AMD/PSP signatures are NOT validated here.
    return Error::None;
}
}
#endif
