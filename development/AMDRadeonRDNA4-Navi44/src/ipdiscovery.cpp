// Allocation-free Discovery parser, BSD-3-Clause; original LICENSE retained.
// Format pin: Linux 24a19b953e2a3d0ea5a8c4951a0ab8f32720c907 discovery.h.
// No register access. Caller retains immutable input for the view lifetime.
#include "ipdiscovery.hpp"

namespace {
bool inside(size_t n, size_t off, size_t count) { return off <= n && count <= n - off; }
uint16_t u16(const uint8_t *p) { return uint16_t(p[0]) | uint16_t(p[1]) << 8; }
uint32_t u32(const uint8_t *p) { return uint32_t(u16(p)) | uint32_t(u16(p + 2)) << 16; }
uint64_t u64(const uint8_t *p) { return uint64_t(u32(p)) | uint64_t(u32(p + 4)) << 32; }
uint16_t sum(const uint8_t *p, size_t n) {
    uint16_t value = 0;
    for (size_t i = 0; i < n; ++i) value = uint16_t(value + p[i]);
    return value;
}
}

bool IpDiscovery::fail(const char *why) {
    valid = false; numIps = 0; haveGc = false;
    binBase = dieBase = binEnd = ipEnd = 0;
    lastError = why;
    return false;
}

bool IpDiscovery::readU8(size_t off, uint8_t &v) const {
    if (!data || !inside(size, off, 1)) return false;
    v = data[off]; return true;
}
bool IpDiscovery::readU16(size_t off, uint16_t &v) const {
    if (!data || !inside(size, off, 2)) return false;
    v = u16(data + off); return true;
}
bool IpDiscovery::readU32(size_t off, uint32_t &v) const {
    if (!data || !inside(size, off, 4)) return false;
    v = u32(data + off); return true;
}

bool IpDiscovery::initBinary(const uint8_t *buffer, size_t bufferSize) {
    data = buffer; size = bufferSize;
    fail("not_initialized");
    if (!data || !inside(size, 0, 12)) return fail("out_of_bounds");
    return validateBinary(0);
}

bool IpDiscovery::init(const uint8_t *buffer, size_t bufferSize) {
    data = buffer; size = bufferSize;
    fail("not_initialized");
    if (!data || size < 12) return fail("out_of_bounds");
    // Legacy ROM scan, bounded in subtraction form. Exact host input uses initBinary.
    for (size_t off = 0; off <= size - 12; off += 4) {
        if (u32(data + off) == 0x28211407 && validateBinary(off)) return true;
    }
    return fail("binary_magic");
}

bool IpDiscovery::validateBinary(size_t offset) {
    if (!inside(size, offset, 12)) return fail("out_of_bounds");
    const uint8_t *d = data + offset;
    const size_t available = size - offset;
    if (u32(d) != 0x28211407) return fail("binary_magic");
    majorVersion = u16(d + 4); minorVersion = u16(d + 6);
    if ((majorVersion == 1 && minorVersion > 3) ||
        (majorVersion == 2 && minorVersion != 0) || (majorVersion != 1 && majorVersion != 2))
        return fail("binary_version");
    const size_t n = u16(d + 10);
    if (!inside(available, 0, n)) return fail("out_of_bounds");
    const size_t start = majorVersion == 1 ? 12 : 16;
    if (majorVersion == 2 && !inside(available, 12, 2)) return fail("out_of_bounds");
    const uint16_t count = majorVersion == 1 ? 6 : u16(d + 12);
    if (!count || count > 6) return fail("table_count");
    if (majorVersion == 2 && u16(d + 14)) return fail("binary_reserved");
    if (!inside(n, start, size_t(count) * 8)) return fail("out_of_bounds");
    if (sum(d + 10, n - 10) != u16(d + 8)) return fail("binary_checksum");
    uint16_t offsets[6] {}, lengths[6] {};
    for (uint16_t i = 0; i < count; ++i) {
        const uint8_t *t = d + start + i * 8;
        const uint16_t off = u16(t), checksum = u16(t + 2), length = u16(t + 4);
        if (u16(t + 6)) return fail("table_reserved");
        if (!off && !checksum && !length) continue;
        if (!off || !length || off < start + count * 8) return fail("table_range");
        if (!inside(n, off, length)) return fail("out_of_bounds");
        for (uint16_t j = 0; j < i; ++j)
            if (lengths[j] && off < size_t(offsets[j]) + lengths[j] && offsets[j] < size_t(off) + length)
                return fail("table_overlap");
        if (sum(d + off, length) != checksum) return fail("table_checksum");
        offsets[i] = off; lengths[i] = length;
    }
    if (!lengths[0]) return fail("missing_ipds");
    const size_t off = offsets[0], length = lengths[0], end = off + length;
    if (length < 80) return fail("out_of_bounds");
    if (u32(d + off) != 0x53445049 || u32(d + off + 8) != 0) return fail("ipds_magic_or_id");
    ipVersion = u16(d + off + 4);
    if (ipVersion != 3 && ipVersion != 4) return fail("ipds_version");
    if (u16(d + off + 6) != length || u16(d + off + 12) != 1) return fail("ipds_size_or_die_count");
    const uint8_t flags = d[off + 78];
    if (d[off + 79] || (flags & ~1u) || (ipVersion == 3 && flags)) return fail("ipds_flags");
    addressWidth = (flags & 1) ? 8 : 4;
    const size_t die = u16(d + off + 16);
    if (die < off + 80) return fail("die_offset");
    if (!inside(end, die, 4)) return fail("out_of_bounds");
    const uint16_t ips = u16(d + die + 2);
    if (u16(d + die) != u16(d + off + 14) || !ips || ips > 256) return fail("die_id_or_ip_count");
    size_t p = die + 4;
    for (uint16_t i = 0; i < ips; ++i) {
        if (!inside(end, p, 8)) return fail("out_of_bounds");
        const uint8_t bases = d[p + 3];
        if (!bases || bases > MaxBases) return fail("base_count");
        if (!inside(end, p + 8, size_t(bases) * addressWidth)) return fail("out_of_bounds");
        for (uint8_t b = 0; b < bases; ++b) {
            const uint8_t *base = d + p + 8 + b * addressWidth;
            const uint64_t value = addressWidth == 8 ? u64(base) : u32(base);
            if (value > UINT64_MAX / 4) return fail("register_address_overflow");
        }
        for (uint16_t j = 0; j < i; ++j) {
            const uint8_t *previous = data + entryOffsets[j];
            if (u16(previous) == u16(d + p) && previous[2] == d[p + 2]) return fail("duplicate_ip");
        }
        entryOffsets[i] = offset + p;
        p += 8 + size_t(bases) * addressWidth;
    }
    if (count > 1 && lengths[1]) {
        const size_t gc = offsets[1], glen = lengths[1];
        if (glen < 28) return fail("out_of_bounds");
        const uint16_t a = u16(d + gc + 4), b = u16(d + gc + 6);
        if (u32(d + gc) != 0x4347 || b || (a != 1 && a != 2)) return fail("gc_info_version");
        if (u32(d + gc + 8) != glen || glen < (a == 1 ? 88u : 80u)) return fail("gc_info_size");
        gcSe = u32(d + gc + 12); gcRb = u32(d + gc + 24);
        if (!gcSe || !gcRb) return fail("gc_info_zero");
        haveGc = true; gcVersion = uint32_t(a) << 16 | b;
    }
    binBase = offset; binEnd = offset + n; dieBase = offset + die; ipEnd = offset + end;
    numIps = ips; valid = true; lastError = nullptr;
    return true;
}

bool IpDiscovery::ipAt64(uint16_t index, IpEntry64 &out) const {
    out = IpEntry64 {};
    if (!valid || index >= numIps) return false;
    const uint8_t *p = data + entryOffsets[index];
    out.hwId = u16(p); out.instance = p[2]; out.numBases = p[3];
    out.major = p[4]; out.minor = p[5]; out.revision = p[6];
    for (uint8_t i = 0; i < out.numBases; ++i)
        out.bases[i] = addressWidth == 8 ? u64(p + 8 + i * 8) : u32(p + 8 + i * 4);
    return true;
}
bool IpDiscovery::ipAt(uint16_t index, IpEntry &out) const {
    out = IpEntry {};
    IpEntry64 ip;
    if (!ipAt64(index, ip)) return false;
    for (uint8_t i = 0; i < ip.numBases; ++i) if (ip.bases[i] > UINT32_MAX) return false;
    out.hwId = ip.hwId; out.instance = ip.instance; out.numBases = ip.numBases;
    out.major = ip.major; out.minor = ip.minor; out.revision = ip.revision;
    for (uint8_t i = 0; i < ip.numBases; ++i) out.bases[i] = uint32_t(ip.bases[i]);
    return true;
}
bool IpDiscovery::findIp64(uint16_t hwId, uint8_t instance, IpEntry64 &out) const {
    for (uint16_t i = 0; i < numIps; ++i) {
        if (!ipAt64(i, out)) return false;
        if (out.hwId == hwId && out.instance == instance) return true;
    }
    out = IpEntry64 {}; return false;
}
bool IpDiscovery::findIp(uint16_t hwId, uint8_t instance, IpEntry &out) const {
    for (uint16_t i = 0; i < numIps; ++i) {
        IpEntry64 ip;
        if (!ipAt64(i, ip)) return false;
        if (ip.hwId == hwId && ip.instance == instance) return ipAt(i, out);
    }
    out = IpEntry {}; return false;
}
bool IpDiscovery::gcInfo(uint32_t &se, uint32_t &rb, uint32_t *version) const {
    if (!valid || !haveGc) return false;
    se = gcSe; rb = gcRb; if (version) *version = gcVersion; return true;
}
bool IpDiscovery::regByteOffset64(uint16_t hw, uint8_t instance, uint8_t segment,
                                 uint64_t add, uint64_t &out) const {
    IpEntry64 ip;
    if (!findIp64(hw, instance, ip) || segment >= ip.numBases ||
        add > UINT64_MAX / 4 || ip.bases[segment] > UINT64_MAX / 4 - add) return false;
    out = (ip.bases[segment] + add) * 4; return true;
}
bool IpDiscovery::regByteOffset(uint16_t hw, uint8_t instance, uint8_t segment,
                               uint32_t add, uint32_t &out) const {
    uint64_t value;
    if (!regByteOffset64(hw, instance, segment, add, value) || value > UINT32_MAX) return false;
    out = uint32_t(value); return true;
}
