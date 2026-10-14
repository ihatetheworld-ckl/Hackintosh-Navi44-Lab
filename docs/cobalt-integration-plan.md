# Cobalt / RADV 接口准备：M6.5

N44I v1 为32字节little-endian，C++/Python已有离线验证：magic/version/length、PCI、revision有效位、target、
capabilities=0、reserved=0；未知能力不得发布。没有transport/IOUserClient/selector，非生产N48N ABI。
gfx1200/gfx1201可共享版本化查询协议，但ASIC/IP/topology/固件需求必须独立，不能使用canned gfx1201。

未来可信内核profile→带有效位的真实GC/SE/CU/RB/TCC/GB_ADDR_CONFIG/VRAM/BAR→生产ABI→Darwin RADV。
IP寄存器基址不应混入BAR物理地址字段；没有任意MMIO或物理地址操作接口。
单一驱动拥有GPU power/VM/queue/display，用户态只通过受限BO/submit/fence访问。
VMID生命周期、BO隔离、复位和并发需要未来单独验证，本轮没有实现真实资源所有权。
Cobalt PR12、bundle/cache和私有Metal接入仍是此前固定研究状态，未应用/运行。
