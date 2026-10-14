# 跨语言差分验证

Python生产参考函数和C++真实编译probe分别读取相同bytes；C++不调用Python也不复制其输出。
canonical JSON比较接受/拒绝、binary/IPDS版本、地址宽度、IP实例/版本/base、GC_INFO；
另比较profile、firmware结构/需求、ELF/descriptor与N44I。
错误码在共同支持格式内也需一致；Unsupported不是假PASS。
537个共享case在 reports/m65/shared-corpus.json；多数为截断/错误输入，不等于537份实机fixture。
2400次seed759065变异同样比较，两实现最终零差异；尚未使用coverage-guided libFuzzer。
地址高位用JSON整数精确保留，避免浮点路径。
回归m65-invalid-strtab.bin：合成kernel ELF字符串表声明越界，源生成规则在synthetic.py/统一入口。
