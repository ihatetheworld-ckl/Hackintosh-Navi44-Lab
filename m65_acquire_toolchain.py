"""Download official archive, verify publisher-hosted digest, safe unpack only.
No installers, post-install scripts or external commands are executed.
"""
from pathlib import Path, PurePosixPath
import hashlib, json, urllib.request, zipfile
ROOT=Path(__file__).resolve().parent
BASE=ROOT/'tools/toolchains'
BASE.mkdir(parents=True,exist_ok=True)
name='llvm-mingw-20261006-ucrt-x86_64.zip'
url='https://github.com/mstorsjo/llvm-mingw/releases/download/20261006/'+name
expected='317492c456aa27ee607a5919f1d2d38dcdc1112516a24d0bf4b00d078f52d17a'
archive=BASE/name
if not archive.exists():
    with urllib.request.urlopen(url,timeout=60) as r, archive.open('wb') as out:
        count=0
        while block:=r.read(1024*1024):
            count+=len(block)
            if count>200_000_000: raise ValueError('Download limit')
            out.write(block)
digest=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()
if digest!=expected: raise ValueError('SHA256 mismatch; refusing extraction/execution')
destination=BASE/'llvm'
if destination.exists(): raise ValueError('Toolchain directory exists; refusing overwrite')
with zipfile.ZipFile(archive) as z:
    infos=z.infolist()
    if sum(i.file_size for i in infos)>3_000_000_000: raise ValueError('Extraction size limit')
    for i in infos:
        p=PurePosixPath(i.filename)
        if p.is_absolute() or '..' in p.parts or ':' in i.filename or '\\' in i.filename:
            raise ValueError('Unsafe archive path')
        if (i.external_attr>>16)&0o170000 == 0o120000: raise ValueError('Archive symlink')
    destination.mkdir()
    z.extractall(destination)
record={'project':'mstorsjo/llvm-mingw','tag':'20261006','url':url,
        'sha256':digest,'expected_sha256':expected,'verified':True,
        'verification_source':'GitHub official release asset digest via API, not detached signature',
        'archive_bytes':archive.stat().st_size,'portable':True,'installer_executed':False}
(ROOT/'reports/m65/toolchain-provenance.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record,indent=2))
