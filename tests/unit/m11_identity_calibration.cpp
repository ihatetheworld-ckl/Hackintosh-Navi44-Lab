// Single-thread CPU calibration against actual M10/current source, BSD-3-Clause.
#include "lifecycle.hpp"
#include <iostream>
using namespace NaviPlatform;using namespace NaviCore;
int main(){
    struct Resource{uint8_t bytes[16]{};unsigned references{1};} a,b;
    AccessOps gate{{nullptr,[](void*){return true;},[](void*){}},[](void*){return true;}};
    auto ops=[](Resource&r){return ReferenceOps{&r,[](void*p){++static_cast<Resource*>(p)->references;return true;},
        [](void*p){--static_cast<Resource*>(p)->references;},[](void*p,View&v){v={static_cast<Resource*>(p)->bytes,16};return success();},nullptr,nullptr};};
    SnapshotOwner x(gate,1),y(gate,1);x.activate(ops(a));y.activate(ops(b));SnapshotTicket tx{},ty{};x.borrow(tx);y.borrow(ty);View v{};
    bool cross=y.read(tx,v).ok();std::cout<<"CROSS_OWNER_READ_ALLOWED "<<cross<<'\n';
    x.giveBack(tx);y.giveBack(ty);x.close();y.close();return cross?1:0;
}
