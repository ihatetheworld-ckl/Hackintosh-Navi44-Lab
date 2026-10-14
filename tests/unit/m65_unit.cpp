// Actual C++ behavior tests, BSD-3-Clause. No devices or GPU libraries.
#include "asicprofile.hpp"
#include "ipdiscovery.hpp"
#include "offlinevalidation.hpp"
#include "codeobj.hpp"
#include <iostream>
#include <vector>
#include <cstring>
void w16(std::vector<uint8_t> &d, size_t p, uint16_t v) { d[p]=uint8_t(v); d[p+1]=uint8_t(v>>8); }
void w32(std::vector<uint8_t> &d, size_t p, uint32_t v) { w16(d,p,uint16_t(v)); w16(d,p+2,uint16_t(v>>16)); }
void w64(std::vector<uint8_t> &d, size_t p, uint64_t v) { w32(d,p,uint32_t(v)); w32(d,p+4,uint32_t(v>>32)); }
uint16_t sum(const std::vector<uint8_t>& d,size_t p,size_t n) { uint16_t s=0; for(size_t i=p;i<p+n;++i)s=uint16_t(s+d[i]); return s; }
std::vector<uint8_t> fixture(bool wide=false, uint64_t base=0x100) {
    std::vector<uint8_t> d(344); w32(d,0,0x28211407); w16(d,4,1); w16(d,10,uint16_t(d.size()));
    w16(d,12,128); w16(d,16,wide?100:96); w16(d,20,256); w16(d,24,88);
    w32(d,128,0x53445049); w16(d,132,wide?4:3); w16(d,134,wide?100:96);
    w16(d,140,1); w16(d,144,208); d[206]=wide?1:0;
    w16(d,210,1); w16(d,212,11); d[215]=1; d[216]=12;
    if(wide)w64(d,220,base); else w32(d,220,uint32_t(base));
    w32(d,256,0x4347); w16(d,260,1); w32(d,264,88); w32(d,268,2); w32(d,280,2);
    w16(d,14,sum(d,128,wide?100:96)); w16(d,22,sum(d,256,88)); w16(d,8,sum(d,10,d.size()-10));
    return d;
}
int main() {
    unsigned passed=0, failed=0;
    auto check=[&](const char *name,bool result){ std::cout<<(result?"PASS ":"FAIL ")<<name<<'\n'; result?++passed:++failed; };
    using namespace Asic;
    check("navi44_identity",identify(0x1002,0x7590).target==Target::Gfx1200);
    check("navi48_7550",identify(0x1002,0x7550).target==Target::Gfx1201);
    check("navi48_7551",identify(0x1002,0x7551).family==Family::Navi48);
    check("unknown_device",identify(0x1002,0xffff).family==Family::Unknown);
    check("revision_unverified",!identify(0x1002,0x7590,3,true).revisionVerified);
    check("topology_unknown",!identify(0x1002,0x7590).topology.verified);
    check("hardware_permanently_disabled",!hardwareInitializationAllowed());
    IpDiscovery parser; auto d=fixture();
    check("discovery_valid",parser.initBinary(d.data(),d.size()));
    IpDiscovery::IpEntry old{}; check("legacy_entry",parser.ipAt(0,old)&&old.bases[0]==0x100);
    uint32_t se=0,rb=0; check("gc_info",parser.gcInfo(se,rb)&&se==2&&rb==2);
    const char *manifestError=nullptr; Offline::FirmwareRequirement needs[16] {}; size_t needCount=0;
    check("manifest_missing_ip",!Offline::firmwareRequirements(identify(0x1002,0x7590),parser,needs,needCount,&manifestError)&&needCount==0);
    check("manifest_wrong_gc",!Offline::firmwareRequirements(identify(0x1002,0x7550),parser,needs,needCount,&manifestError));
    auto wide=fixture(true,UINT64_C(0x100000000));
    check("discovery_64",parser.initBinary(wide.data(),wide.size()));
    IpDiscovery::IpEntry64 ip{}; check("high_bits_preserved",parser.ipAt64(0,ip)&&ip.bases[0]==UINT64_C(0x100000000));
    check("legacy_narrow_rejected",!parser.ipAt(0,old));
    uint64_t byte=0; check("64bit_byte_offset",parser.regByteOffset64(11,0,0,1,byte)&&byte==UINT64_C(0x400000004));
    uint32_t narrow=0; check("32bit_offset_rejected",!parser.regByteOffset(11,0,0,1,narrow));
    check("address_overflow_rejected",!parser.regByteOffset64(11,0,0,UINT64_MAX,byte));
    bool truncations=true; for(size_t i=0;i<d.size();++i)truncations &= !parser.initBinary(d.data(),i);
    check("all_truncations",truncations);
    check("failure_clears_state",!parser.isValid()&&parser.ipCount()==0);
    d=fixture(); d.back()^=1; check("bad_checksum",!parser.initBinary(d.data(),d.size()));
    const char *why=nullptr; std::vector<uint8_t> fw(36); w32(fw,0,36);w32(fw,4,32);w16(fw,8,1);
    w16(fw,12,12);w32(fw,20,4);w32(fw,24,32);
    check("firmware_header",Offline::firmware(fw.data(),fw.size(),12,0,"pfp",&why));
    check("firmware_wrong_ip",!Offline::firmware(fw.data(),fw.size(),13,0,"pfp",&why));
    check("firmware_unknown_component",!Offline::firmware(fw.data(),fw.size(),12,0,"unknown",&why));
    w32(fw,28,1);check("firmware_crc_fail_closed",!Offline::firmware(fw.data(),fw.size(),12,0,"pfp",&why));
    uint8_t bad[64]{};check("elf_bad_header",!Offline::elf(bad,64,Target::Gfx1200,&why));
    check("elf_unknown_target",!Offline::elf(bad,64,Target::Unknown,&why));
    CodeObj::Image image{};check("old_codeobj_rejects",!CodeObj::parseImage(bad,64,image,&why));
    Offline::Session session;check("state_cannot_jump",!session.advance(Offline::State::OfflineReady)&&session.state==Offline::State::Failed);
    check("failed_terminal",!session.advance(Offline::State::PciMatched));
    Offline::Session good;
    bool transitions=good.advance(Offline::State::PciMatched)&&good.advance(Offline::State::ProfileValidated)&&
        good.advance(Offline::State::DiscoveryValidated)&&good.advance(Offline::State::FirmwareRequirementsValidated)&&good.advance(Offline::State::OfflineReady);
    check("offline_sequence",transitions);
    check("ready_terminal",!good.advance(Offline::State::Failed));
    std::vector<uint8_t> abi(32);std::memcpy(abi.data(),"N44I",4);w16(abi,4,1);w16(abi,6,32);
    w16(abi,8,0x1002);w16(abi,10,0x7590);w16(abi,14,0x48);Profile p{};
    check("abi_navi44",Offline::deviceInfo(abi.data(),abi.size(),p,&why)&&p.target==Target::Gfx1200);
    w64(abi,16,1);check("abi_capability_rejected",!Offline::deviceInfo(abi.data(),abi.size(),p,&why));
    std::cout<<"SUMMARY "<<passed<<' '<<failed<<'\n';return failed?1:0;
}
