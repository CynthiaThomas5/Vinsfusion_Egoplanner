// Compile against the pinned Agent FramingIO and its hardware-only resync patch.
#include <uxr/agent/transport/stream_framing/StreamFramingProtocol.hpp>
#include <algorithm>
#include <cassert>
#include <cstring>
#include <iostream>
#include <vector>
using namespace eprosima::uxr;
using Bytes = std::vector<uint8_t>;
static uint16_t crc(const Bytes& bytes) {
    uint16_t c=0;
    for (auto b:bytes) { c^=b; for (int i=0;i<8;++i) c=(c>>1)^((c&1)?0xa001:0); }
    return c;
}
static Bytes frame(const Bytes& payload) {
    Bytes raw={1,0,uint8_t(payload.size()),uint8_t(payload.size()>>8)};
    raw.insert(raw.end(),payload.begin(),payload.end());
    auto c=crc(payload);raw.push_back(uint8_t(c));raw.push_back(uint8_t(c>>8));
    Bytes wire={0x7e};
    for(auto b:raw) { if(b==0x7e||b==0x7d) {wire.push_back(0x7d);wire.push_back(b^0x20);} else wire.push_back(b); }
    return wire;
}
static std::vector<Bytes> decode(const Bytes& wire,size_t chunk) {
    size_t pos=0;
    FramingIO io(0,[](uint8_t*,size_t n,TransportRc&){return ssize_t(n);},
        [&](uint8_t* b,size_t n,int,TransportRc& rc)->ssize_t {
            size_t k=std::min({n,chunk,wire.size()-pos});
            if(!k){rc=TransportRc::timeout_error;return 0;}
            std::memcpy(b,wire.data()+pos,k);pos+=k;return ssize_t(k);
        });
    std::vector<Bytes> result;
    // Drain buffered bytes after the callback reaches EOF as well.
    for(size_t calls=0;calls<wire.size()+4;++calls) {
        uint8_t b[4096],remote=0;int timeout=1000;TransportRc rc=TransportRc::ok;
        size_t n=io.read_framed_msg(b,sizeof(b),remote,timeout,rc);
        if(n){assert(remote==1);result.emplace_back(b,b+n);}
        if(pos==wire.size()&&!n&&rc==TransportRc::timeout_error)break;
    }
    return result;
}
int main() {
    Bytes ping={0x81,0,0,0,2,1,8,0,0,10,0xff,0xfd,2,0,0,0};
    Bytes escaped={0x81,0x7e,0x7d,0,0x7e,0x7d};
    std::vector<Bytes> prefixes={{},{0x7e},{0x7e,1},{0x7e,1,0},{0x7e,1,0,16},
        {0x7e,1,0,16,0,0x81,0},{0x7e,1,0,0,0},{0x7e,1,0,0,0,0}};
    size_t checked=0;
    for(size_t chunk: {size_t(1),size_t(2),size_t(5),size_t(41)}) {
        assert(decode(frame(ping),chunk)==std::vector<Bytes>{ping});
        assert(decode(frame(escaped),chunk)==std::vector<Bytes>{escaped});
        Bytes broken=frame(ping);broken.back()^=1;
        assert(decode(broken,chunk).empty());
        for(auto wire:prefixes) {
            auto valid=frame(ping);wire.insert(wire.end(),valid.begin(),valid.end());
            assert(decode(wire,chunk)==std::vector<Bytes>{ping});++checked;
        }
        auto valid=frame(ping);broken.insert(broken.end(),valid.begin(),valid.end());
        assert(decode(broken,chunk)==std::vector<Bytes>{ping});
    }
    std::cout<<checked<<" resync cases plus CRC/escaping checks passed\n";
}
