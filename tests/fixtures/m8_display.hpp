// Synthetic bytes only. No hardware captures, serials, firmware upload or commands.
#ifndef Navi44M8Fixtures_hpp
#define Navi44M8Fixtures_hpp
#include <array>
#include <vector>
#include <stdint.h>
namespace M8Fixture {
template<class B>void w16(B&b,size_t p,uint16_t v){b[p]=uint8_t(v);b[p+1]=uint8_t(v>>8);}
template<class B>void seal(B&b,size_t offset=0,size_t size=128){
    uint8_t sum=0;b[offset+size-1]=0;for(size_t i=0;i<size-1;++i)sum=uint8_t(sum+b[offset+i]);
    b[offset+size-1]=uint8_t(0-sum);
}
inline std::array<uint8_t,128> edid(){
    std::array<uint8_t,128>b{};for(unsigned i=1;i<7;++i)b[i]=255;
    uint16_t id=(14u<<10)|(22u<<5)|9;b[8]=uint8_t(id>>8);b[9]=uint8_t(id);
    w16(b,10,44);b[18]=1;b[19]=4;b[20]=0x80;
    for(unsigned i=38;i<54;++i)b[i]=1;
    for(unsigned i=0;i<4;++i)b[54+18*i+3]=0x10;
    const uint8_t d[]={0x02,0x3a,0x80,0x18,0x71,0x38,0x2d,0x40,88,44,0x45,0,0,0,0,0,0,0x1e};
    for(unsigned i=0;i<18;++i)b[54+i]=d[i];seal(b);return b;
}
inline std::vector<uint8_t> cta(unsigned blocks=1){
    auto base=edid();base[126]=uint8_t(blocks);seal(base);
    std::vector<uint8_t>b(base.begin(),base.end());b.resize((blocks+1)*128);
    for(unsigned n=1;n<=blocks;++n){
        size_t off=n*128;b[off]=2;b[off+1]=3;b[off+2]=6;
        b[off+4]=0x41;b[off+5]=16;seal(b,off);
    }return b;
}
inline std::vector<uint8_t> displayId1440p180(){
    auto base=edid();base[126]=1;seal(base);
    std::vector<uint8_t>b(base.begin(),base.end());b.resize(256,0);
    size_t off=128;
    b[off]=0x70;    // DisplayID EDID extension tag
    b[off+1]=0x13;  // DisplayID v1.3
    b[off+2]=23;    // section payload bytes: 3-byte block header + 20-byte timing
    b[off+3]=0x03;  // primary use: gaming/display
    b[off+4]=0x00;  // extension count
    b[off+5]=0x01;  // Type I Detailed Timing Data Block
    b[off+6]=0x00;  // revision 0
    b[off+7]=20;    // 1 descriptor * 20 bytes
    // 2560x1440 @ 180Hz: hActive=2560, hBlank=160 (hTotal=2720), hOffset=48, hSync=32
    // vActive=1440, vBlank=60 (vTotal=1500), vOffset=3, vSync=5
    // pixelClockKHz = 734400 -> rawClk = 73440 - 1 = 73439 (0x011EDF)
    const uint32_t rawClk=73439u;
    size_t d=off+8;
    b[d+0]=uint8_t(rawClk&0xff);b[d+1]=uint8_t((rawClk>>8)&0xff);b[d+2]=uint8_t((rawClk>>16)&0xff);
    b[d+3]=0x80; // preferred, progressive, no stereo
    w16(b,d+4,2560-1);w16(b,d+6,160-1);
    w16(b,d+8,uint16_t((48-1)|0x8000));w16(b,d+10,32-1);
    w16(b,d+12,1440-1);w16(b,d+14,60-1);
    w16(b,d+16,uint16_t((3-1)|0x8000));w16(b,d+18,5-1);
    // DisplayID section checksum at off + 4 + 23 = off + 28: sum(off+1 .. off+28) == 0 mod 256
    uint8_t didSum=0;
    for(size_t i=off+1;i<off+28;++i)didSum=uint8_t(didSum+b[i]);
    b[off+28]=uint8_t(0-didSum);
    seal(b,off,128);
    return b;
}
inline std::array<uint8_t,1024> rom(){
    std::array<uint8_t,1024>b{};b[0]=0x55;b[1]=0xaa;b[2]=2;w16(b,0x48,0x80);
    w16(b,0x80,40);b[0x82]=2;b[0x83]=2;b[0x84]='A';b[0x85]='T';b[0x86]='O';b[0x87]='M';
    w16(b,0xa0,0x100);w16(b,0x100,74);b[0x102]=2;b[0x103]=1;
    w16(b,0x104+22*2,0x180);w16(b,0x180,60);b[0x182]=1;b[0x183]=5;
    w16(b,0x184,0x88);b[0x186]=2;
    for(unsigned i=0;i<2;++i){
        size_t p=0x188+i*16;w16(b,p,i?0x310c:0x3113);w16(b,p+2,uint16_t(40+i*10));
        w16(b,p+4,uint16_t(0x2120+i));w16(b,p+12,i?0x80:8);
        size_t r=0x180+40+i*10;const uint8_t raw[]={1,4,uint8_t(0x90+i),0,2,4,uint8_t(i+1),1,0xff,0};
        for(unsigned j=0;j<10;++j)b[r+j]=raw[j];
    }seal(b,0,b.size());return b;
}
}
#endif
