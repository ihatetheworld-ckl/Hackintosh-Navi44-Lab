# gfx1200 / ELF：M6.5

固定 LLVM ELF.h 核验 gfx1200=0x048、gfx1201=0x04e；不重标记二进制。
保留 CodeObj 的 expected 参数与旧默认 gfx1201。

新增 C++ Offline::elf / elfKernel，与 Python validate_elf / validate_kernel 独立实现并差分。
先检查完整 section file envelope，再 metadata，再符号和 descriptor，避免损坏结构诊断顺序不一致。
校验 ET_DYN/AMDGPU、target、PT_LOAD、section/note、UTF-8/MsgPack 子集、metadata 版本1.0..1.2、
name/symbol/kernarg、选定 kernel 的 descriptor entry 与符号、kernarg/group/private 大小一致性。
CodeObj 修复有符号 entry 偏移溢出/下溢，并拒绝 NOBITS 当作文件代码。

严格 host API 没有自动接入现有 kext 的全部 loader 调用；完整 relocations/AMDHSA/shader 语义仍未覆盖。
完整 synthetic kernel ELF 是格式测试数据，不是 AMD 指令或编译产物。
已下载工具链没有 AMDGPU backend，真正 gfx1200 产物测试仍 SKIP；不运行 GPU API。
