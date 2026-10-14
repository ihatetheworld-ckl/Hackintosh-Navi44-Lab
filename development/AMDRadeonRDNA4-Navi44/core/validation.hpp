// Kernel-friendly CPU data core, BSD-3-Clause. No STL/heap/exceptions/IO.
#ifndef Navi44CoreValidation_hpp
#define Navi44CoreValidation_hpp
#include <stdint.h>
#include <stddef.h>
#include "../src/asicprofile.hpp"
namespace NaviCore {
enum class Error : uint8_t { None, Bounds, Format, Unsupported, Mismatch, Missing, Budget, Protocol };
struct Result {
    Error code; const char *detail; uint64_t offset;
    constexpr bool ok() const { return code == Error::None; }
};
constexpr Result success() { return {Error::None,nullptr,0}; }
constexpr Result failure(const char *s, Error e=Error::Format,uint64_t p=0) { return {e,s,p}; }
struct View {
    const uint8_t *data; size_t size;
    bool inside(uint64_t off,uint64_t count) const { return (data || !size) && off<=size && count<=size-off; }
    Result slice(uint64_t off,uint64_t count,View &out) const {
        out={nullptr,0};
        if (!inside(off,count)) return failure("out_of_bounds",Error::Bounds,off);
        out={count?data+off:nullptr,size_t(count)};return success();
    }
};
enum class Kind : uint8_t { Number, String, Map, Array };
struct Node {
    Kind kind; uint16_t child, next, count; uint64_t number; View text;
};
struct Scratch { Node *nodes; size_t capacity, used; };
// Scratch and immutable input are caller-owned and must outlive the call.
// No borrowed Node/View is returned. Failure resets scratch.used to zero.
Result elf(View,Asic::Target,Scratch&,View kernelName={nullptr,0});
Result firmware(View,uint16_t,uint16_t,View component);
Result deviceInfo(View,Asic::Profile&);
struct PackagePart { uint32_t type,version; View payload; };
struct Package { PackagePart parts[13]; uint32_t count; bool signatureVerified; };
Result pspPackage(View,Package&);
constexpr bool hardwareAllowed() { return false; }
static_assert(sizeof(uint64_t)==8,"fixed-width types required");
static_assert(sizeof(Asic::Target)==1,"target layout");
}
#endif
