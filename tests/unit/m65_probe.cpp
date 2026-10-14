// CPU-only stdin protocol. BSD-3-Clause. Never loads a device or driver.
#include "ipdiscovery.hpp"
#include "offlinevalidation.hpp"
#include "../../development/AMDRadeonRDNA4-Navi44/core/validation.hpp"
#include "../../development/AMDRadeonRDNA4-Navi44/core/device_info.hpp"
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

std::vector<uint8_t> unhex(const std::string &s) {
    if (s.size() > (2u << 20) || s.size() % 2) throw std::runtime_error("input_size");
    std::vector<uint8_t> out;
    for (size_t i = 0; i < s.size(); i += 2) {
        auto nibble = [](char c) -> unsigned {
            if (c >= '0' && c <= '9') return c - '0';
            if (c >= 'a' && c <= 'f') return c - 'a' + 10;
            throw std::runtime_error("input_hex");
        };
        out.push_back(uint8_t(nibble(s[i]) * 16 + nibble(s[i + 1])));
    }
    return out;
}
void failure(const char *why) { std::cout << "{\"ok\":false,\"error\":\"" << why << "\"}\n"; }
void success() { std::cout << "{\"ok\":true}\n"; }
int main() {
    std::string line;
    while (std::getline(std::cin, line)) {
        try {
            if (line.size() > (2u << 20) + 128) throw std::runtime_error("input_size");
            std::istringstream in(line); std::string mode, hex; in >> mode;
            unsigned a = 0, b = 0; std::string component;
            if (mode == "elf" || mode == "kernel" || mode == "manifest") in >> a;
            if (mode == "elfbudget") in >> a >> b;
            if (mode == "firmware") in >> a >> b >> component;
            if (mode == "profile") {
                unsigned revision = 257; in >> a >> b >> revision;
                if (revision > 256) { failure("revision_range"); continue; }
                if (a != 0x1002) { failure("unknown_vendor"); continue; }
                if (b > 65535) { failure("unknown_device"); continue; }
                const auto p = Asic::identify(uint16_t(a), uint16_t(b), uint8_t(revision), revision != 256);
                if (p.family == Asic::Family::Unknown) { failure("unknown_device"); continue; }
                std::cout << "{\"ok\":true,\"asic\":\"" << (p.family == Asic::Family::Navi44 ? "Navi44" : "Navi48")
                          << "\",\"target\":" << unsigned(p.target) << ",\"revision\":";
                if (p.revisionKnown) std::cout << unsigned(p.revision); else std::cout << "null";
                std::cout << ",\"capabilities\":0}\n"; continue;
            }
            in >> hex; auto bytes = unhex(hex);
            const char *error = nullptr;
            if(mode=="elfbudget") {
                NaviCore::Node nodes[512];NaviCore::Scratch scratch{nodes,b>512?512:b,0};
                auto result=NaviCore::elf({bytes.data(),bytes.size()},Asic::Target(a),scratch);
                if(result.ok())success();else failure(result.detail);
            } else if (mode == "psp") {
                NaviCore::Package package{};
                auto result=NaviCore::pspPackage({bytes.data(),bytes.size()},package);
                if(!result.ok()){failure(result.detail);continue;}
                std::cout<<"{\"ok\":true,\"signature_verified\":false,\"parts\":[";bool comma=false;
                for(unsigned i=1;i<=12;++i)if(package.parts[i].payload.size){auto p=package.parts[i];if(comma)std::cout<<',';comma=true;
                    std::cout<<'['<<i<<','<<p.version<<','<<p.payload.data-bytes.data()-uint32_t(bytes[24]|uint32_t(bytes[25])<<8|uint32_t(bytes[26])<<16|uint32_t(bytes[27])<<24)<<','<<p.payload.size<<']';}
                std::cout<<"]}\n";
            } else if(mode=="abi2") {
                NaviCore::DeviceInfo info{};auto result=NaviCore::decodeDeviceInfo({bytes.data(),bytes.size()},info);
                if(!result.ok()){failure(result.detail);continue;}
                std::cout<<"{\"ok\":true,\"target\":"<<unsigned(info.profile.target)<<",\"present\":"<<info.present
                         <<",\"gc\":["<<unsigned(info.gcMajor)<<','<<unsigned(info.gcMinor)<<','<<unsigned(info.gcRevision)
                         <<"],\"topology\":["<<info.se<<','<<info.cu<<','<<info.rb<<','<<info.tcc<<','<<info.gbAddrConfig
                         <<"],\"memory\":["<<info.vramBytes<<','<<info.visibleBarBytes<<"],\"capabilities\":0}\n";
            } else if (mode == "manifest") {
                IpDiscovery parser;
                if (!parser.initBinary(bytes.data(),bytes.size())) { failure(parser.error()); continue; }
                const auto profile = Asic::identify(0x1002,uint16_t(a));
                if (profile.family == Asic::Family::Unknown) { failure("unknown_device"); continue; }
                Offline::FirmwareRequirement needs[16] {}; size_t count=0;
                if (!Offline::firmwareRequirements(profile,parser,needs,count,&error)) { failure(error); continue; }
                std::cout << "{\"ok\":true,\"requirements\":[";
                for (size_t i=0;i<count;++i) {
                    if(i)std::cout<<',';
                    std::cout<<"[\""<<needs[i].block<<"\",\""<<needs[i].component<<"\","<<unsigned(needs[i].ip.major)
                             <<','<<unsigned(needs[i].ip.minor)<<','<<unsigned(needs[i].ip.revision)<<']';
                }
                std::cout<<"]}\n";
            } else if (mode == "discovery") {
                IpDiscovery parser;
                if (!parser.initBinary(bytes.data(), bytes.size())) { failure(parser.error()); continue; }
                std::cout << "{\"ok\":true,\"binary_version\":[" << parser.binaryMajor() << ',' << parser.binaryMinor()
                          << "],\"ipds_version\":" << parser.ipdsVersion() << ",\"address_bits\":" << unsigned(parser.addressBits()) << ",\"ips\":[";
                for (uint16_t i = 0; i < parser.ipCount(); ++i) {
                    IpDiscovery::IpEntry64 ip;
                    if (!parser.ipAt64(i, ip)) throw std::runtime_error("iteration_failure");
                    if (i) std::cout << ',';
                    std::cout << '[' << ip.hwId << ',' << unsigned(ip.instance) << ',' << unsigned(ip.major) << ',' << unsigned(ip.minor)
                              << ',' << unsigned(ip.revision) << ",[";
                    for (unsigned j = 0; j < ip.numBases; ++j) { if (j) std::cout << ','; std::cout << ip.bases[j]; }
                    std::cout << "]]";
                }
                std::cout << "],\"gc_info\":";
                uint32_t se = 0, rb = 0;
                if (parser.gcInfo(se, rb)) std::cout << '[' << se << ',' << rb << ']'; else std::cout << "null";
                std::cout << "}\n";
            } else if (mode == "elf") {
                if (a != 0x48 && a != 0x4e) { failure("unknown_target"); continue; }
                if (Offline::elf(bytes.data(), bytes.size(), Asic::Target(a), &error)) success(); else failure(error);
            } else if (mode == "kernel") {
                if (a != 0x48 && a != 0x4e) { failure("unknown_target"); continue; }
                if (Offline::elfKernel(bytes.data(),bytes.size(),Asic::Target(a),"synthetic",&error)) success(); else failure(error);
            } else if (mode == "firmware") {
                if (Offline::firmware(bytes.data(), bytes.size(), uint16_t(a), uint16_t(b), component.c_str(), &error)) success(); else failure(error);
            } else if (mode == "abi") {
                Asic::Profile p;
                if (Offline::deviceInfo(bytes.data(), bytes.size(), p, &error)) {
                    std::cout << "{\"ok\":true,\"target\":" << unsigned(p.target) << ",\"capabilities\":0}\n";
                } else failure(error);
            } else failure("unknown_mode");
        } catch (const std::exception &e) { failure(e.what()); }
    }
}
