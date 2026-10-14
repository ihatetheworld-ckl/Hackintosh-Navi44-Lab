// Genuine Kernel.framework API/ownership compile probe, BSD-3-Clause.
// Object only. Never linked, loaded or called; not a runtime lifetime test.
#include "../../development/AMDRadeonRDNA4-Navi44/platform/darwin_native.hpp"
#include <libkern/c++/OSObject.h>
#include <libkern/c++/OSData.h>
#include <IOKit/IOBufferMemoryDescriptor.h>

static_assert(sizeof(IOReturn) == 4, "real IOReturn width");
static_assert(sizeof(void*) == 8, "64-bit kernel target");
static_assert(sizeof(NaviPlatform::NodePool) <= 65536, "owner storage budget");

namespace NaviDarwin {
// Validate actual OSObject and buffer reference APIs without mock Apple types.
void descriptorReferenceCompileCheck(IOBufferMemoryDescriptor& buffer) {
    buffer.retain();
    buffer.release();
}
NaviCore::View dataReferenceCompileCheck(const OSData& data) {
    data.retain();
    const auto size = data.getLength();
    const auto bytes = data.getBytesNoCopy();
    // The returned View is deliberately empty after release: no dangling lease.
    (void)size;
    (void)bytes;
    data.release();
    return {nullptr, 0};
}
}
