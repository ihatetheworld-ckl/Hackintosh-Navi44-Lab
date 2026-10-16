// Real isolated negative objects; never executed or included in production link.
#if defined(N44_POLICY_HOST)
#include <cstdio>
int n44PolicyHost(){return std::puts("policy negative");}
#elif defined(N44_POLICY_UNKNOWN)
extern "C" int n44_unlisted_import();
int n44PolicyUnknown(){return n44_unlisted_import();}
#elif defined(N44_POLICY_EXCEPTION)
int n44PolicyException(){throw 7;}
#elif defined(N44_POLICY_RTTI)
struct N44PolicyBase{virtual ~N44PolicyBase()=default;};struct N44PolicyDerived:N44PolicyBase{};
bool n44PolicyRtti(N44PolicyBase*p){return dynamic_cast<N44PolicyDerived*>(p)!=nullptr;}
#elif defined(N44_POLICY_PRINTF)
#include <libkern/libkern.h>
int n44PolicyPrintf(unsigned x){return printf("%u",x);}
#elif defined(N44_POLICY_PROVIDER)
extern "C" int n44_policy_required(){return 17;}
#elif defined(N44_POLICY_CONSUMER)
extern "C" int n44_policy_required();
int n44PolicyConsumer(){return n44_policy_required();}
#elif defined(N44_POLICY_INITIALIZER)
extern "C" int n44_unlisted_import();
int n44_policy_value;struct N44PolicyInit{N44PolicyInit(){n44_policy_value=n44_unlisted_import();}} n44_initializer;
#endif
