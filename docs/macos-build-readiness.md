# M8 macOS Build Readiness / M9

Windows已真实编译：既有ASIC/Discovery/CodeObj/validation/device_info，
新增EDID/AtomBIOS/display/integrity/query_candidate及不含Apple SDK的Platform contract。
9个Core translation unit使用C++17、-fno-exceptions、-fno-rtti、-ffreestanding、
-Wall/-Wextra/-Werror和4096B单函数栈警告，并审查object undefined symbols。
仍有memcpy/memset和内部Core引用。总递归栈、Mach-O、Apple symbol/ABI仍未验证。
Host tests/STL/exception wrapper不进入kernel target；Darwin native不进入Windows target。

~~~mermaid
flowchart TD
    A[合法Xcode / Apple SDK / fixed KernelSDK] --> B[真实macOS Core compile only]
    C[Explicit CPU source list / no hardware backend] --> B
    B --> D[Mach-O symbol / layout / stack check]
    D --> E[CPU fixture / lifetime tests on macOS]
    E --> F[Darwin thread / OSData ownership wrapper review]
    F --> G[未来独立kext build授权]
    G --> H[未来独立load / hardware授权]
~~~

M9建议优先真实macOS的CPU编译与纯逻辑测试，而不是先堆积寄存器初始化：
1. 用户明确指定合法、已具备Xcode/SDK的Mac及授权工作区；本轮不自动连接。
2. 只编译Core和adapter object，确认真实头、固定宽度、missing symbols、constructor/teardown。
3. 复跑同一合成fixtures和CPU-only测试；不签名、不安装、不加载kext。
4. 解决NodePool堆生命周期、OSData/descriptor retain、ExecutionOps gate和kernel stack预算。
5. 再研究kext target与版本适配；独立授权不可由此自动获得。

AMDRadeonRDNA4固定Makefile参考macOS11 ABI。MacKernelSDK pin
05094e5e88cec7caedbfb35e8449ed0db94bf95b；Lilu pin0515f40b7f2a096adc85e832a4c6104fbd07f936。
固定SDK README基于macOS11/Xcode12.0头，不能推出新Xcode/Sequoia/Tahoe实际兼容。
没有Windows交叉kext build、fake Apple SDK、自动上传或远程CI。
KernelSDK native/object compile = NOT RUN；kext build/load = NOT RUN。

若暂时没有合法Mac，Windows仍可针对DisplayID、真实合法静态样本、Atom其他版本、
CRC格式来源、parser budget继续有限研发；这些不能替代真实Darwin构建。
