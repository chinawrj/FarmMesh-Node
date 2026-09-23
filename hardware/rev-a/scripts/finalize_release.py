#!/usr/bin/env python3
"""Seal/verify the exact A1 package; never grant approval or edit RELEASE.md.

After export and visual/expert review, update RELEASE.md separately as authorized,
then run this script. It refreshes only the named release documents/review evidence,
rechecks frozen sources and all payload hashes, and writes a deterministic ZIP plus
an external ZIP SHA256. --check-only changes no files and checks an existing ZIP.
Any native/BOM/parts/script change requires a new verification and export.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

from export_manufacturing import (BASE, OUT, DOCS, all_payload_files, copy_documents,
                                 require, require_same_sources, seal_manifest,
                                 sha, verify_closure)

ARCHIVE = BASE/'FarmMesh-Node-A1-manufacturing.zip'
PREFIX = 'FarmMesh-Node-A1/'


def release_status():
    text=(BASE/'RELEASE.md').read_text(encoding='utf-8')
    lines=[line for line in text.splitlines() if re.search(r'\bstatus\s*:',line,re.I)]
    require(bool(lines),'RELEASE.md must explicitly state its status')
    return lines[0]


def verify_zip(path, folder):
    expected={PREFIX+p.relative_to(folder).as_posix():sha(p) for p in all_payload_files(folder)}
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        require(len(names)==len(set(names)),'Duplicate ZIP members')
        require(set(names)==set(expected),'ZIP contents do not exactly match the sealed package')
        require(z.testzip() is None,'ZIP CRC check failed')
        for name,digest in expected.items():
            require(hashlib.sha256(z.read(name)).hexdigest()==digest,f'ZIP member hash mismatch: {name}')
    return expected


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only',action='store_true',help='Read-only verification of tree, native sources, ZIP and external ZIP SHA')
    parser.add_argument('--review-file',action='append',default=[],type=Path,
                        help='Explicit current A1 review evidence under reports/ or review/; repeat as needed')
    args=parser.parse_args()
    require(not (args.check_only and args.review_file),'--check-only cannot add evidence')
    m=verify_closure(OUT);require_same_sources(m['frozen_source_sha256'])
    require(m.get('assembly_count')==153 and m.get('board_feature_count')==11 and m.get('smd_count')==147,'Unexpected A1 BOM coverage')
    checksum=Path(str(ARCHIVE)+'.sha256')
    if args.check_only:
        for rel in DOCS:
            require(sha(BASE/rel)==sha(OUT/'documentation'/rel)==sha(OUT/'native'/rel),f'Release documentation changed after sealing: {rel}')
        for rel,digest in m.get('review_evidence_source_sha256',{}).items():
            require(sha(BASE/rel)==digest,f'Review evidence changed after sealing: {rel}')
        require(ARCHIVE.is_file() and checksum.is_file(),'Archive or external checksum missing')
        verify_zip(ARCHIVE,OUT)
        require(checksum.read_text()==f'{sha(ARCHIVE)}  {ARCHIVE.name}\n','External ZIP checksum mismatch')
        print(json.dumps({'verified':str(ARCHIVE),'sha256':sha(ARCHIVE),'board_sha256':m['board_sha256'],'release_status_line':m.get('release_status_line')}))
        return
    document_hashes={rel:sha(BASE/rel) for rel in DOCS}
    evidence={}
    evidence_copies=[]
    for path in args.review_file:
        source=(BASE/path).resolve() if not path.is_absolute() else path.resolve()
        require(source.is_relative_to(BASE),'Review evidence must be inside rev-a')
        rel=source.relative_to(BASE)
        require(rel.parts[0] in ('reports','review') and source.is_file(),'Review evidence must be a file under reports/ or review/')
        require(source.suffix.lower() in {'.md','.json','.pdf','.png','.svg','.txt','.csv'},'Unsupported review-evidence format')
        require(not re.search(r'(^|[-_])A0([._-]|$)',source.name,re.I),'Old A0 review evidence is not allowed')
        dest=OUT/'review/evidence'/rel
        evidence[rel.as_posix()]=sha(source);evidence_copies.append((source,dest))
    copy_documents(OUT)
    for source,dest in evidence_copies:
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    m['status']='sealed_snapshot_release_authority_is_RELEASE_md'
    m['release_status_line']=release_status()
    m['release_document_sha256']=document_hashes['RELEASE.md']
    m['review_evidence_source_sha256']={**m.get('review_evidence_source_sha256',{}),**evidence}
    m['archive_policy']='Sorted entries; fixed ZIP timestamp 1980-01-01; UNIX 0644; deflate level 9. No absolute paths, symlinks, ZIPs or old output trees are imported.'
    seal_manifest(OUT,m);verify_closure(OUT)
    require_same_sources(m['frozen_source_sha256'])
    with tempfile.NamedTemporaryFile(prefix='.FarmMesh-Node-A1-',suffix='.zip',dir=BASE,delete=False) as f:
        temp=Path(f.name)
    try:
        with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for p in all_payload_files(OUT):
                info=zipfile.ZipInfo(PREFIX+p.relative_to(OUT).as_posix(),date_time=(1980,1,1,0,0,0))
                info.create_system=3;info.external_attr=0o100644<<16
                info.compress_type=zipfile.ZIP_DEFLATED
                z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
        verify_zip(temp,OUT);verify_closure(OUT);require_same_sources(m['frozen_source_sha256'])
        require(document_hashes=={rel:sha(BASE/rel) for rel in DOCS},'Release documentation changed while packaging')
        for rel,digest in m['review_evidence_source_sha256'].items():
            require(sha(BASE/rel)==digest,f'Review evidence changed while packaging: {rel}')
        temp.replace(ARCHIVE)
        checksum.write_text(f'{sha(ARCHIVE)}  {ARCHIVE.name}\n')
        print(json.dumps({'sealed_archive':str(ARCHIVE),'archive_sha256':sha(ARCHIVE),
                          'board_sha256':m['board_sha256'],'release_status_line':m['release_status_line'],
                          'approval_changed':False},ensure_ascii=False))
    finally:
        if temp.exists():temp.unlink()


if __name__=='__main__':
    try:main()
    except Exception as error:raise SystemExit(f'PACKAGE ABORTED: {error}')
