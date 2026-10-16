"""M13 explicit SDK26/profile and dependency policy. BSD-3-Clause.

Read installed SDK only. Metadata is SDK evidence, never target-kernel evidence.
"""
import hashlib,json,plistlib
from pathlib import Path
import m7_safety as safe
PROFILE=json.loads(safe.checked('config/m13-target.json').read_text())
def sdk_info(path):
    root=Path(path).resolve(strict=True)
    settings=json.loads((root/'SDKSettings.json').read_text())
    if settings['Version']!=PROFILE['sdk_version']:raise ValueError('SDK_VERSION_MISMATCH')
    system=plistlib.loads((root/'System/Library/CoreServices/SystemVersion.plist').read_bytes())
    if system['ProductVersion']!=PROFILE['sdk_version']:raise ValueError('SDK_METADATA_MISMATCH')
    kernel=root/PROFILE['kernel_headers'];headers=['IOKit/IOService.h','IOKit/IOLocks.h','IOKit/IOLib.h','IOKit/IOBufferMemoryDescriptor.h','libkern/c++/OSObject.h','libkern/c++/OSMetaClass.h','libkern/c++/OSData.h','IOKit/IORegistryEntry.h']
    hashes={}
    for rel in headers:
        p=(kernel/rel).resolve(strict=True)
        if not p.is_relative_to(root):raise ValueError('KERNEL_HEADER_ESCAPE')
        hashes[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
    return dict(root=str(root),version=settings['Version'],SDK_build=system['ProductBuildVersion'],kernel=str(kernel),header_sha256=hashes,
        Kernel_framework='PRESENT',target_binary_verified=False,settings_sha256=hashlib.sha256((root/'SDKSettings.json').read_bytes()).hexdigest())
def dependency(path,sdk,resource,host=False,host_cpp=None):
    p=Path(path).resolve(strict=True)
    if p.is_relative_to(safe.ROOT.resolve()):return 'PROJECT'
    if p.is_relative_to(Path(sdk).resolve()):return 'SDK26'
    if p.is_relative_to(Path(resource).resolve()):return 'APPLE_COMPILER_BUILTIN'
    if host and host_cpp and p.is_relative_to(Path(host_cpp).resolve()):return 'APPLE_HOST_STDLIB'
    raise ValueError('UNAPPROVED_HEADER_OR_MIXED_SDK: '+str(p))
def object_target(image):
    wanted=tuple(int(v) for v in PROFILE['deployment_target'].split('.'))
    minimum=(wanted[0]<<16)|(wanted[1]<<8)
    sdk=(26<<16)|(5<<8)
    if not image['versions'] or any(v['platform']!=1 or v['minimum']!=minimum or v['sdk']!=sdk for v in image['versions']):raise ValueError('OBJECT_TARGET_VERSION_MISMATCH')
def reference(data):
    if data['pin']!=PROFILE['xnu_pin']:raise ValueError('REFERENCE_VERSION_MISMATCH')
    expected={f['path']:f['sha256'] for f in json.loads(safe.checked('reports/m13/reference-manifest.json').read_text())['files']}
    if {f['path'] for f in data['files']}!=set(expected):raise ValueError('REFERENCE_FILESET_MISMATCH')
    for f in data['files']:
        actual=hashlib.sha256(f['text'].encode()).hexdigest()
        if f.get('sha256')!=actual or actual!=expected[f['path']]:raise ValueError('REFERENCE_HASH_MISMATCH')
