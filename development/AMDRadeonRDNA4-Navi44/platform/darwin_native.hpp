// Future real Kernel SDK only. Not part of any Windows build. BSD-3-Clause.
#ifndef Navi44DarwinNative_hpp
#define Navi44DarwinNative_hpp
#if !defined(__APPLE__) || !defined(KERNEL)
#error Requires a separately authorized genuine Darwin kernel build
#endif
#include "contract.hpp"
#include <IOKit/IOReturn.h>
namespace NaviDarwin {
NaviPlatform::MemoryOps nativeMemoryOps();
NaviPlatform::LogOps nativeLogOps();
// Caller-owned constructed pool; owner must provide serialized thread context.
NaviPlatform::ScratchOps nativeScratchOps(NaviPlatform::NodePool&);
IOReturn nativeError(NaviCore::Result);
}
#endif
