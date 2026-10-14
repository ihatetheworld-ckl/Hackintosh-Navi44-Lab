// Genuine Apple metadata, for offline file analysis only. BSD-3-Clause.
// No service registration or hardware. Both entry functions refuse execution.
#include <mach/kmod.h>
extern "C" {
kern_return_t n44_offline_start(kmod_info_t*,void*){return KERN_FAILURE;}
kern_return_t n44_offline_stop(kmod_info_t*,void*){return KERN_FAILURE;}
KMOD_EXPLICIT_DECL(org.navi44.offline.linkcheck,"0.0.0",n44_offline_start,n44_offline_stop)
}
