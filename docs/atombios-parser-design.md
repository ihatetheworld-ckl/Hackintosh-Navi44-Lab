# M8 AtomBIOS Static Parser

在原AtomBios类上加固，Core connectors()转发到它，不创建重复ROM解析器。
支持静态55AA legacy image、512B块长度、镜像sum8、
ATOM ROM header2.2/2.3已知前缀、master data table2.1的35个entry、
display object info1.5 path_v3（16B）、I2C与HPD静态records和DP/HDMI等connector类型。
读取的是调用方不可变CPU字节，不执行command bytecode。

镜像输入最大4MiB，在512B边界扫描；遇到带签名但无效的image停止，不自动绕过损坏主镜像。
读表范围限定选中的legacy image，不允许借更大的外层buffer逃逸。
验证ATOM/master header长度版本、表offset/common size、表间/控制表重叠、自引用与重复alias。
路径最多8个、storage不超8个；connector重复/错误对象类型/reserved/path count拒绝。
record不得指向path array；每步至少2B、最多128步、必须终止；重复I2C/HPD和非法size拒绝。
unknown record仅按长度有限跳过，不解释为PHY支持。USBC特殊reserved配置当前拒绝，保留为未支持。
输出先暂存，成功后commit；失败清空ConnectorList/paths。借用ROM仅存在于Parser对象寿命内。

修正master table枚举：DCE index27、VRAM28、VoltageObject32，
由AMD公开atomfirmware.h的v2.1字段顺序核对。Display v1.4 path_v2不再混作v1.5。
其他table只验证通用边界，不宣称完整字段语义或所有ATOM版本兼容。
legacy checksum不是固件真实性或PSP签名认证。

不支持完整PCI PCIR多image链验证、完整PSP包/ROM board authentication、
其他display object版本、encoder/PHY实际routing、GPIO寄存器使用、执行ATOM函数。
没有读取本机ROM，也未使用其他板卡ROM映射冒充Navi44结果。
真实Navi44 VBIOS与connector routing = UNVERIFIED；本轮数据全部合成。

[AMD atomfirmware.h](https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/amd/include/atomfirmware.h)
用于布局交叉检查，2026-10-14阅读，master为移动参考；
已有AMDRadeonRDNA4源码commit49f7f20c为工程基础（E2）。
文件头既有Navi48验证描述属于上游历史，不是本轮、本机测试声明。
