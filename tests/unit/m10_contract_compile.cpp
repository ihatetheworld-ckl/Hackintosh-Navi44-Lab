// Kernel-options compile only. No entry point, OS service, or deployment.
#include "../../development/AMDRadeonRDNA4-Navi44/platform/darwin_snapshot.hpp"
#include "../../development/AMDRadeonRDNA4-Navi44/platform/darwin_native.hpp"
static_assert(sizeof(NaviCore::Error)==1,"fixed errors");
static_assert(sizeof(NaviPlatform::OwnerState)==1,"fixed states");
static_assert(sizeof(void*)==8,"64-bit Darwin");
static_assert(sizeof(NaviPlatform::SnapshotOwner)<4096,"small ownership metadata");
static_assert(sizeof(NaviPlatform::NodePool)<65536,"separate caller-owned scratch");
NaviCore::Result m10CompileContract(NaviDarwin::NativeSnapshot&source,NaviCore::View input){
    return source.createCopy(input,NaviDarwin::CpuSnapshotStorage::DataCopy);
}
