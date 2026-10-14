// Refactored M6.5 validation, BSD-3-Clause. No OS/STL/exception dependencies.
#include "validation.hpp"
#include "model.hpp"
#include "../src/codeobj.hpp"
namespace NaviCore {
namespace {
constexpr uint16_t nil=UINT16_MAX;
uint16_t u16(const uint8_t*p){return uint16_t(p[0])|uint16_t(p[1])<<8;}
uint32_t u32(const uint8_t*p){return uint32_t(u16(p))|uint32_t(u16(p+2))<<16;}
uint64_t u64(const uint8_t*p){return uint64_t(u32(p))|uint64_t(u32(p+4))<<32;}
size_t literalSize(const char*s){size_t n=0;while(s[n])++n;return n;}
bool same(View a,View b){if(a.size!=b.size)return false;for(size_t i=0;i<a.size;++i)if(a.data[i]!=b.data[i])return false;return true;}
bool eq(View a,const char*s){return same(a,{reinterpret_cast<const uint8_t*>(s),literalSize(s)});}
bool utf8(View s){
    for(size_t i=0;i<s.size;){uint32_t c=s.data[i++];if(c<0x80)continue;
        unsigned rest;uint32_t minimum;
        if(c>=0xc2&&c<=0xdf){rest=1;minimum=0x80;c&=31;}
        else if(c>=0xe0&&c<=0xef){rest=2;minimum=0x800;c&=15;}
        else if(c>=0xf0&&c<=0xf4){rest=3;minimum=0x10000;c&=7;}else return false;
        if(rest>s.size-i)return false;
        while(rest--){uint8_t b=s.data[i++];if((b&0xc0)!=0x80)return false;c=(c<<6)|(b&63);}
        if(c<minimum||c>0x10ffff||(c>=0xd800&&c<=0xdfff))return false;
    }return true;
}
class Metadata {
    View input;Scratch& arena;size_t position{0};
    Result big(unsigned width,uint64_t&x){
        if(!input.inside(position,width))return failure("out_of_bounds",Error::Bounds,position);
        x=0;while(width--)x=(x<<8)|input.data[position++];return success();
    }
    Result parse(unsigned depth,uint16_t&index){
        if(depth>16)return failure("metadata_depth",Error::Budget,position);
        if(!input.inside(position,1))return failure("out_of_bounds",Error::Bounds,position);
        if(!arena.nodes||arena.used>=arena.capacity||arena.used>=nil)return failure("metadata_budget",Error::Budget,position);
        index=uint16_t(arena.used++);arena.nodes[index]={Kind::Number,nil,nil,0,0,{nullptr,0}};
        const uint8_t tag=input.data[position++];Node&node=arena.nodes[index];
        if(tag<0x80){node.number=tag;return success();}
        if((tag>=0xa0&&tag<=0xbf)||tag==0xd9||tag==0xda||tag==0xdb){
            uint64_t length=tag&31;Result r=success();
            if(tag>0xbf)r=big(tag==0xd9?1:tag==0xda?2:4,length);
            if(!r.ok())return r;
            View text;r=input.slice(position,length,text);if(!r.ok())return r;position+=size_t(length);
            if(!utf8(text))return failure("metadata_utf8");node.kind=Kind::String;node.text=text;return success();
        }
        const bool map=(tag>=0x80&&tag<=0x8f)||tag==0xde||tag==0xdf;
        const bool array=(tag>=0x90&&tag<=0x9f)||tag==0xdc||tag==0xdd;
        if(map||array){uint64_t count=tag&15;Result r=success();
            if(tag>=0xa0)r=big(tag==0xdc||tag==0xde?2:4,count);
            if(!r.ok())return r;if(count>4096)return failure("metadata_count",Error::Budget);
            node.kind=map?Kind::Map:Kind::Array;node.count=uint16_t(count);uint16_t previous=nil;
            for(uint64_t i=0;i<count;++i){uint16_t key;r=parse(depth+1,key);if(!r.ok())return r;
                if(map){
                    if(arena.nodes[key].kind!=Kind::String)return failure("metadata_key");
                    for(uint16_t p=node.child;p!=nil;){if(same(arena.nodes[p].text,arena.nodes[key].text))return failure("metadata_key");
                        const uint16_t value=arena.nodes[p].next;p=arena.nodes[value].next;}
                    uint16_t value;r=parse(depth+1,value);if(!r.ok())return r;
                    arena.nodes[key].next=value;
                    if(previous==nil)node.child=key;else arena.nodes[previous].next=key;previous=value;
                }else{if(previous==nil)node.child=key;else arena.nodes[previous].next=key;previous=key;}
            }return success();
        }
        if(tag>=0xcc&&tag<=0xcf)return big(1u<<(tag-0xcc),node.number);
        return failure("metadata_encoding_unsupported",Error::Unsupported);
    }
    uint16_t field(uint16_t map,const char*key)const{
        if(map==nil||arena.nodes[map].kind!=Kind::Map)return nil;
        for(uint16_t p=arena.nodes[map].child;p!=nil;){const uint16_t value=arena.nodes[p].next;
            if(eq(arena.nodes[p].text,key))return value;p=arena.nodes[value].next;}
        return nil;
    }
    bool number(uint16_t n)const{return n!=nil&&arena.nodes[n].kind==Kind::Number;}
    bool text(uint16_t n)const{return n!=nil&&arena.nodes[n].kind==Kind::String&&arena.nodes[n].text.size;}
public:
    Metadata(View v,Scratch&s):input(v),arena(s){}
    Result validate(View elf,Asic::Target target,View selected){
        arena.used=0;uint16_t root;Result r=parse(0,root);if(!r.ok())return r;
        if(position!=input.size||arena.nodes[root].kind!=Kind::Map)return failure("metadata_envelope");
        uint16_t version=field(root,"amdhsa.version"),kernels=field(root,"amdhsa.kernels");
        if(version==nil||arena.nodes[version].kind!=Kind::Array||arena.nodes[version].count!=2)return failure("metadata_version_missing");
        uint16_t a=arena.nodes[version].child,b=arena.nodes[a].next;
        if(!number(a)||!number(b))return failure("metadata_version_missing");
        if(arena.nodes[a].number!=1||arena.nodes[b].number>2)return failure("metadata_version_unsupported",Error::Unsupported);
        if(kernels==nil||arena.nodes[kernels].kind!=Kind::Array||!arena.nodes[kernels].count)return failure("metadata_kernels_missing");
        bool found=false;
        for(uint16_t k=arena.nodes[kernels].child;k!=nil;k=arena.nodes[k].next){
            uint16_t name=field(k,".name"),symbol=field(k,".symbol"),argument=field(k,".kernarg_segment_size");
            if(!text(name)||!text(symbol))return failure("metadata_kernel_identity_missing");
            if(!number(argument)||arena.nodes[argument].number>UINT32_MAX)return failure("metadata_kernarg_missing");
            if(!selected.size||!same(arena.nodes[name].text,selected))continue;
            if(found)return failure("elf_kernel_metadata_duplicate");found=true;
            View sym=arena.nodes[symbol].text;
            if(sym.size!=selected.size+3)return failure("elf_kernel_symbol_mismatch",Error::Mismatch);
            for(size_t i=0;i<selected.size;++i)if(sym.data[i]!=selected.data[i])return failure("elf_kernel_symbol_mismatch",Error::Mismatch);
            if(sym.data[selected.size]!='.'||sym.data[selected.size+1]!='k'||sym.data[selected.size+2]!='d')return failure("elf_kernel_symbol_mismatch",Error::Mismatch);
            if(selected.size>127)return failure("elf_kernel_metadata_missing",Error::Unsupported);
            char key[128];for(size_t i=0;i<selected.size;++i)key[i]=char(selected.data[i]);key[selected.size]=0;
            CodeObj::Kernel kernel{};const char*why=nullptr;
            if(!CodeObj::findKernel(elf.data,elf.size,key,kernel,&why,target))return failure("elf_descriptor_invalid");
            if(arena.nodes[argument].number!=kernel.kernargSize)return failure("elf_descriptor_mismatch",Error::Mismatch);
            const char*keys[]={".group_segment_fixed_size",".private_segment_fixed_size"};
            const uint32_t values[]={kernel.groupSegmentSize,kernel.privateSegmentSize};
            for(unsigned i=0;i<2;++i){uint16_t f=field(k,keys[i]);if(f!=nil&&(!number(f)||arena.nodes[f].number!=values[i]))return failure("elf_descriptor_mismatch",Error::Mismatch);}
        }
        if(selected.size&&!found)return failure("elf_kernel_metadata_missing",Error::Missing);
        return success();
    }
};
Result elfImpl(View v,Asic::Target target,Scratch&scratch,View selected){
    if(target!=Asic::Target::Gfx1200&&target!=Asic::Target::Gfx1201)return failure("unknown_target",Error::Unsupported);
    if(v.size>(16u<<20))return failure("elf_input_budget",Error::Budget);
    if(!v.inside(0,64)||!v.data)return failure("out_of_bounds",Error::Bounds);
    const uint8_t*d=v.data;const uint8_t ident[]={0x7f,'E','L','F',2,1,1};
    for(unsigned i=0;i<7;++i)if(d[i]!=ident[i])return failure("elf_ident");
    if(u16(d+16)!=3||u16(d+18)!=224||u32(d+20)!=1)return failure("elf_type_machine_version");
    if((u32(d+48)&255)!=uint32_t(target))return failure("elf_target_mismatch",Error::Mismatch);
    const uint16_t ps=u16(d+54),pc=u16(d+56),ss=u16(d+58),sc=u16(d+60);
    const uint64_t po=u64(d+32),so=u64(d+40);
    if(u16(d+52)!=64||ps!=56||ss!=64||!pc||!sc)return failure("elf_tables_missing");
    if(uint32_t(pc)+sc>4096)return failure("elf_table_budget",Error::Budget);
    if(!v.inside(po,uint64_t(ps)*pc)||!v.inside(so,uint64_t(ss)*sc))return failure("out_of_bounds",Error::Bounds);
    for(unsigned i=0;i<sc;++i){const uint8_t*s=d+so+uint64_t(i)*ss;if(u32(s+4)!=8&&!v.inside(u64(s+24),u64(s+32)))return failure("out_of_bounds",Error::Bounds);}
    for(unsigned i=0;i<sc;++i){const uint8_t*s=d+so+uint64_t(i)*ss;const uint32_t kind=u32(s+4),link=u32(s+40);const uint64_t n=u64(s+32),entry=u64(s+56);
        if((kind==2||kind==11)&&n){if(entry<24||n%entry||link>=sc||u32(d+so+uint64_t(link)*ss+4)!=3)return failure("elf_symbols_invalid");}
        if((kind==4||kind==9)&&n){const uint64_t expected=kind==4?24:16;
            if(entry!=expected||n%entry||link>=sc||u32(s+44)>=sc)return failure("elf_relocations_invalid");
            const uint8_t*symbols=d+so+uint64_t(link)*ss;uint32_t type=u32(symbols+4);uint64_t stride=u64(symbols+56),size=u64(symbols+32);
            if((type!=2&&type!=11)||stride<24||size%stride)return failure("elf_relocations_invalid");
            for(uint64_t p=0;p<n;p+=entry)if((u64(d+u64(s+24)+p+8)>>32)>=size/stride)return failure("elf_relocations_invalid");
            if(u64(s+8)&2)return failure("elf_relocations_unsupported",Error::Unsupported);
        }
    }
    unsigned loads=0;bool metadata=false;
    for(unsigned i=0;i<pc;++i){const uint8_t*p=d+po+uint64_t(i)*ps;if(u32(p)!=1)continue;
        const uint64_t off=u64(p+8),va=u64(p+16),file=u64(p+32),mem=u64(p+40);
        if(!v.inside(off,file)||va>(16u<<20)||mem>(16u<<20)-va)return failure("out_of_bounds",Error::Bounds);
        if(!file||file>mem)return failure("elf_load_size");++loads;
    }
    for(unsigned i=0;i<sc;++i){const uint8_t*s=d+so+uint64_t(i)*ss;if(u32(s+4)!=7)continue;
        const uint64_t off=u64(s+24),length=u64(s+32),end=off+length;uint64_t p=off;
        while(p<end){if(p>end||12>end-p)return failure("out_of_bounds",Error::Bounds);
            uint64_t names=u32(d+p),descs=u32(d+p+4);uint32_t type=u32(d+p+8);
            uint64_t name=p+12,desc=name+((names+3)&~uint64_t(3)),next=desc+((descs+3)&~uint64_t(3));
            if(name>end||names>end-name||desc>end||descs>end-desc||next>end)return failure("out_of_bounds",Error::Bounds);
            const uint8_t owner[]={ 'A','M','D','G','P','U',0 };bool matched=names==7;
            if(matched)for(unsigned j=0;j<7;++j)matched=matched&&d[name+j]==owner[j];
            if(matched&&type==32&&descs){if(metadata)return failure("elf_duplicate_metadata");
                Result r=Metadata({d+desc,size_t(descs)},scratch).validate(v,target,selected);if(!r.ok())return r;metadata=true;}
            p=next;
        }
    }
    if(!loads||!metadata)return failure("elf_load_or_metadata_missing",Error::Missing);
    return success();
}
}
Result elf(View v,Asic::Target t,Scratch&s,View name){
    s.used=0;if(name.size&&!name.data)return failure("out_of_bounds",Error::Bounds);
    Result r=elfImpl(v,t,s,name);if(!r.ok())s.used=0;return r;
}
Result firmware(View v,uint16_t major,uint16_t minor,View component){
    if(!v.inside(0,32)||!v.data)return failure("out_of_bounds",Error::Bounds);
    const uint8_t*d=v.data;if(u16(d+8)!=1||u16(d+10)!=0)return failure("firmware_header_version",Error::Unsupported);
    uint32_t size=u32(d),header=u32(d+4),count=u32(d+20),off=u32(d+24);
    if(size!=v.size||header<32||header>size||off<header||!count)return failure("firmware_size");
    if(!v.inside(off,count))return failure("out_of_bounds",Error::Bounds);
    if(u16(d+12)!=major||u16(d+14)!=minor)return failure("firmware_ip_mismatch",Error::Mismatch);
    const char*allowed[]={"pfp","me","mec","rlc","imu","mes","mes1","sos","ta","smu","sdma","dmub"};bool known=false;
    if(component.data)for(auto c:allowed)known=known||eq(component,c);
    if(!known)return failure("firmware_component_unsupported",Error::Unsupported);
    if(u32(d+28))return failure("firmware_crc_unverified",Error::Unsupported);return success();
}
Result deviceInfo(View v,Asic::Profile&out){
    out=Asic::identify(0,0);if(!v.data||v.size!=32)return failure("abi_size");const uint8_t*d=v.data;
    if(d[0]!='N'||d[1]!='4'||d[2]!='4'||d[3]!='I'||u16(d+4)!=1||u16(d+6)!=32||d[13]>1||u64(d+16)||u64(d+24))return failure("abi_header_or_capabilities");
    if(u16(d+8)!=0x1002)return failure("unknown_vendor",Error::Unsupported);
    auto p=Asic::identify(u16(d+8),u16(d+10),d[12],d[13]!=0);
    if(p.family==Asic::Family::Unknown)return failure("unknown_device",Error::Unsupported);
    if(u16(d+14)!=uint16_t(p.target)||(!d[13]&&d[12]))return failure("abi_target_or_revision",Error::Mismatch);out=p;return success();
}
Result pspPackage(View v,Package&out){
    out=Package{};if(!v.data||!v.inside(0,36))return failure("firmware_package_bounds",Error::Bounds);
    const uint8_t*d=v.data;const uint32_t size=u32(d),header=u32(d+4),payload=u32(d+24),length=u32(d+20);
    const uint16_t major=u16(d+8),minor=u16(d+10);
    if(major!=2||minor>1)return failure("firmware_package_version",Error::Unsupported);
    const size_t base=minor==1?40:36;
    if(size!=v.size||header<base||header>size||payload<header||!length||!v.inside(payload,length))return failure("firmware_package_bounds",Error::Bounds);
    if(u32(d+28))return failure("firmware_crc_unverified",Error::Unsupported);
    uint32_t count=u32(d+32);if(!count||count>12||!v.inside(base,uint64_t(count)*16)||header<base+uint64_t(count)*16)return failure("firmware_package_count");
    if(minor==1&&u32(d+36))return failure("firmware_package_aux_unverified",Error::Unsupported);
    Package result{};
    for(uint32_t i=0;i<count;++i){const uint8_t*p=d+base+i*16;const uint32_t type=u32(p),version=u32(p+4),offset=u32(p+8),n=u32(p+12);
        if(!type||type>12||!n)return failure("firmware_package_component",Error::Unsupported);
        if(result.parts[type].payload.size)return failure("firmware_package_duplicate");
        if(offset>length||n>length-offset)return failure("firmware_package_bounds",Error::Bounds);
        for(uint32_t j=1;j<=12;++j)if(result.parts[j].payload.size){const uint64_t old=result.parts[j].payload.data-v.data;
            if(uint64_t(payload)+offset<old+result.parts[j].payload.size&&old<uint64_t(payload)+offset+n)return failure("firmware_package_overlap");}
        result.parts[type]={type,version,{d+uint64_t(payload)+offset,n}};
    }
    if(!result.parts[1].payload.size||!result.parts[2].payload.size)return failure("firmware_package_required_missing",Error::Missing);
    result.count=count;result.signatureVerified=false;out=result;return success();
}
}

NaviCore::Result NaviCore::firmwareRequirements(const Asic::Profile &p, const IpDiscovery &discovery,
                                  FirmwareRequirement (&out)[16], size_t &count) {
    count = 0;
    for (auto &entry : out) entry = {};
    auto fail = [&](const char *w) { count = 0; for (auto &entry : out) entry = {}; return failure(w); };
    const auto expected = Asic::identify(p.vendor, p.device, p.revision, p.revisionKnown);
    if (expected.family == Asic::Family::Unknown || p.family != expected.family || p.target != expected.target || p.capabilities)
        return fail("profile_tampered");
    IpDiscovery::IpEntry64 gc;
    if (!discovery.findIp64(11,0,gc) || gc.major != expected.expectedGc.major ||
        gc.minor != expected.expectedGc.minor || gc.revision != expected.expectedGc.revision) return fail("gc_profile_mismatch");
    uint32_t se = 0, rb = 0;
    if (!discovery.gcInfo(se,rb)) return fail("topology_unknown");
    struct Part { uint16_t hw; const char *block; const char *component; };
    const Part parts[] = {{11,"gc","pfp"},{11,"gc","me"},{11,"gc","mec"},{11,"gc","rlc"},
        {11,"gc","imu"},{11,"gc","mes"},{11,"gc","mes1"},{255,"psp","sos"},{255,"psp","ta"},
        {1,"smu","smu"},{42,"sdma","sdma"},{271,"dcn","dmub"}};
    for (const auto &part : parts) {
        IpDiscovery::IpEntry64 ip;
        if (!discovery.findIp64(part.hw,0,ip)) {
            if (part.hw == 255) return fail("required_ip_missing:psp");
            if (part.hw == 1) return fail("required_ip_missing:smu");
            if (part.hw == 42) return fail("required_ip_missing:sdma");
            if (part.hw == 271) return fail("required_ip_missing:dcn");
            return fail("required_ip_missing:gc");
        }
        out[count++] = {part.block,part.component,{ip.major,ip.minor,ip.revision,true}};
    }
    return success(); // Advisory structural requirements; no firmware signature/load.
}
