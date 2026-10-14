# Windows C++ host构建

便携LLVM-MinGW 20261006 UCRT x86_64，Clang23.1.3；官方release asset SHA256记录在toolchain-provenance.json。
包含C++库、mingw-w64头/import库、LLD和compiler-rt，不需要安装Windows SDK/VS。
项目路径：tools/toolchains/llvm/llvm-mingw-20261006-ucrt-x86_64/。

```powershell
& 'D:\RuntimeEnvironment\mise\mise\data\installs\python\3.12.13\python.exe' -I -B -X utf8 run_all_offline_tests.py
```

实际直接clang++编译，C++17、-Wall -Wextra -Werror、-static -g -O1；完整argv在commands.json。
sanitized增加-fsanitize=address,undefined -fno-omit-frame-pointer。
ASan DLL还依赖libc++/libunwind；仅复制已校验包内DLL到build/m65，不写Windows。
ASAN_OPTIONS的log_path使用项目相对路径，避免盘符冒号被误解析。
stdio显式UTF-8，TMP/TEMP与Clang cache在项目内。
CMakeLists保留CPU-only source列表，未下载/运行CMake和Ninja；直接编译入口是实际验证路径。
