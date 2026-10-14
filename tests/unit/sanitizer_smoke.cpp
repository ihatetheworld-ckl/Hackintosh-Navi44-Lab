// No hardware calls. Minimal runtime-startup diagnosis only.
#include <cstdio>
int main() { std::puts("sanitizer startup reached main"); return 0; }
