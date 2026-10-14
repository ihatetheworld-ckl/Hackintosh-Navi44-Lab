// Hardware-independent host validation. BSD-3-Clause; no IOKit/GPU APIs.
#ifndef Navi44OfflineValidation_hpp
#define Navi44OfflineValidation_hpp
#include <stddef.h>
#include <stdint.h>
#include "asicprofile.hpp"
#include "ipdiscovery.hpp"
#include "../core/model.hpp"
namespace Offline {
bool firmware(const uint8_t *, size_t, uint16_t ipMajor, uint16_t ipMinor,
              const char *component, const char **error);
bool elf(const uint8_t *, size_t, Asic::Target, const char **error);
bool elfKernel(const uint8_t *, size_t, Asic::Target, const char *kernelName, const char **error);
bool deviceInfo(const uint8_t *, size_t, Asic::Profile &, const char **error);
using FirmwareRequirement = NaviCore::FirmwareRequirement;
bool firmwareRequirements(const Asic::Profile &, const IpDiscovery &,
                          FirmwareRequirement (&out)[16], size_t &count, const char **error);
using State = NaviCore::State;
using Session = NaviCore::Session;
}
#endif
