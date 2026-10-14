//
//  ipdiscovery.hpp
//  AMDRadeonRDNA4
//
//  Parser for AMD's IP discovery binary — the authoritative per-card list of
//  IP blocks, their versions, and their register base addresses. Modern
//  amdgpu derives its whole register map from this table at runtime; we do
//  the same instead of hardcoding segment bases.
//
//  Freestanding like AtomBios: no IOKit, no allocation, reads from a caller
//  buffer. Verified against firmware/Sapphire.RX9070XT.16384.241213.rom
//  (binary v1.3 at 0x34900, IPDS version 3, 1 die, 46 IPs — GC v12.0.1,
//  DMU/DCN v4.1.0, NBIF v6.3.1) and cross-checked with Linux
//  drivers/gpu/drm/amd/include/discovery.h and amdgpu_discovery.c.
//
//  The discovery binary lives in the PSP region of the 2 MiB unified flash
//  (before the legacy VBIOS image), so at runtime it is only available when
//  the full ROM dump is injected (ATY,bin_image), not via the expansion ROM.
//  At boot the PSP also copies it to the top of VRAM, which is how amdgpu
//  reads it; that path needs working MMIO first.
//

#ifndef IpDiscovery_hpp
#define IpDiscovery_hpp

#include <stdint.h>
#include <stddef.h>

class IpDiscovery {
public:
	// Hardware IP ids (Linux soc15_hw_ip.h) we care about.
	enum HwId : uint16_t {
		HwMp1    = 1,
		HwGc     = 11,
		HwMmhub  = 34,
		HwOsssys = 40,
		HwHdp    = 41,
		HwSdma0  = 42,
		HwNbif   = 108,
		HwUmc    = 150,
		HwMp0    = 255,
		HwDmu    = 271,   // display micro-unit: the DCN register block
	};

	static constexpr size_t MaxBases = 16;   // MP0/MP1 carry 15 segments

	struct IpEntry {
		uint16_t hwId;
		uint8_t  instance;
		uint8_t  major, minor, revision;
		uint8_t  numBases;
		uint32_t bases[MaxBases];   // dword register segment base addresses
	};
	// Register-segment bases in dword units, NOT PCI BAR physical addresses.
	// New type leaves the legacy IpEntry layout unchanged.
	struct IpEntry64 {
		uint16_t hwId;
		uint8_t instance, major, minor, revision, numBases;
		uint64_t bases[MaxBases];
	};

	// Scans `buffer` for the discovery binary signature (0x28211407),
	// validates the binary checksum and the IPDS table, and locates die 0.
	bool init(const uint8_t *buffer, size_t bufferSize);
	bool initBinary(const uint8_t *buffer, size_t bufferSize);
	const char *error() const { return lastError; }
	uint16_t binaryMajor() const { return majorVersion; }
	uint16_t binaryMinor() const { return minorVersion; }
	uint16_t ipdsVersion() const { return ipVersion; }
	uint8_t addressBits() const { return addressWidth * 8; }
	bool ipAt64(uint16_t index, IpEntry64 &out) const;
	bool findIp64(uint16_t hwId, uint8_t instance, IpEntry64 &out) const;
	bool regByteOffset64(uint16_t hwId, uint8_t instance, uint8_t segment,
	                     uint64_t dwordOffset, uint64_t &byteOffset) const;

	bool isValid() const { return valid; }
	size_t binaryOffset() const { return binBase; }
	uint16_t ipCount() const { return numIps; }

	// Iterate all IPs: index 0..ipCount()-1.
	bool ipAt(uint16_t index, IpEntry &out) const;

	// Find a specific IP block instance.
	bool findIp(uint16_t hwId, uint8_t instance, IpEntry &out) const;

	// The GC table (table_list[1]) as amdgpu_discovery_get_gc_info reads it
	// (amdgpu_discovery.c:2016,2020 for v1; v2 has the same u32 slots): the
	// shader-engine and render-backend-per-SE counts. False if the table is
	// absent or of a version amdgpu does not handle either.
	// `version` (optional) gets the table version as major << 16 | minor.
	// Like amdgpu_discovery_verify_table it requires table_id GC_TABLE_ID.
	bool gcInfo(uint32_t &numSe, uint32_t &numRbPerSe, uint32_t *version = nullptr) const;

	// Convenience: absolute MMIO *byte* offset of a register, given its
	// segment index and dword offset within the segment (the BASE_IDX /
	// reg offset pair from Linux asic_reg headers). Returns false if the
	// IP or segment is absent.
	bool regByteOffset(uint16_t hwId, uint8_t instance, uint8_t segment,
	                   uint32_t regDwordOffset, uint32_t &byteOffset) const;

private:
	const uint8_t *data { nullptr };
	size_t size { 0 };
	size_t binBase { 0 };    // offset of binary_header in data
	size_t dieBase { 0 };
	size_t binEnd { 0 }, ipEnd { 0 };    // offset of die_header in data
	uint16_t numIps { 0 };
	bool valid { false };
	const char *lastError { "not_initialized" };
	uint16_t majorVersion {0}, minorVersion {0}, ipVersion {0};
	uint8_t addressWidth {4};
	size_t entryOffsets[256] {};
	bool haveGc {false};
	uint32_t gcSe {0}, gcRb {0}, gcVersion {0};
	bool fail(const char *why);

	bool validateBinary(size_t offset);

	bool readU8 (size_t off, uint8_t  &v) const;
	bool readU16(size_t off, uint16_t &v) const;
	bool readU32(size_t off, uint32_t &v) const;
};

#endif /* IpDiscovery_hpp */
