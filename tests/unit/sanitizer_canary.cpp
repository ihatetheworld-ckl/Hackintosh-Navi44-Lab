// Intentional CPU-only faults in an isolated test process. NEVER GPU code.
#include <climits>
#include <cstring>
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    if (!std::strcmp(argv[1], "asan")) {
        volatile int index = 8;
        int *p = new int[1]; p[0] = 7;
        int x = p[index]; delete[] p; return x;
    }
    if (!std::strcmp(argv[1], "ubsan")) { volatile int x = INT_MAX; return x + 1; }
    return 2;
}
