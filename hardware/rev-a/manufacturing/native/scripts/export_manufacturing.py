#!/usr/bin/env python3
"""Export frozen A1 sources into a fresh manufacturing tree; never approve release.

1. Finish/fill/save the PCB; export netlist and run verify_design.py, verify_pcb.py.
2. Run this script (KiCad 10). It never saves/refills the source PCB.
3. Visually/expert-review these exact outputs, then run finalize_release.py.
PDFs are generated from the same frozen sources as the fabrication files.
"""
import argparse
import csv
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

BASE = Path(__file__).resolve().parents[1]
CLI = Path(os.environ.get('KICAD_CLI', str(Path.home()/'Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')))
PCB = BASE/'FarmMesh-Node.kicad_pcb'
SCH = BASE/'FarmMesh-Node.kicad_sch'
OUT = BASE/'manufacturing'
FEATURES = {'TP1','TP2','TP3','TP101','TP102','TP103','TP104','H1','H2','H3','H4'}
POSITION_FIELDS = ['Ref','Val','Package','PosX','PosY','Rot','Side']
DOCS = ['FABRICATION.md','FIRST-BOARD-TEST.md','RELEASE.md',
        'reports/a1-power-review.md','reports/a1-rf-digital-review.md','reports/a1-dfm-bom-review.md']
LAYERS = ['F.Cu','In1.Cu','In2.Cu','B.Cu','F.Mask','B.Mask','F.SilkS','B.SilkS','F.Paste','B.Paste','Edge.Cuts']


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')


def natural(ref):
    return [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', ref)]


def sexpr(text):
    """Read native KiCad atoms/lists without altering any source bytes."""
    stack = [[]]
    for token in re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text):
        if token == '(':
            item = []; stack[-1].append(item); stack.append(item)
        elif token == ')':
            require(len(stack)>1, 'Unbalanced native S-expression'); stack.pop()
        else:
            stack[-1].append(json.loads(token) if token.startswith('"') else token)
    require(len(stack)==1 and len(stack[0])==1, 'Malformed native S-expression')
    return stack[0][0]


def children(tree, name):
    return [v for v in tree if isinstance(v,list) and v and v[0]==name]


def board_inventory(path=PCB):
    tree = sexpr(path.read_text(encoding='utf-8'))
    result = {}
    for fp in children(tree, 'footprint'):
        fields = {v[1]:v[2] for v in children(fp,'property')}
        ref = fields.get('Reference')
        require(ref and ref not in result, f'Duplicate/missing board reference: {ref}')
        attrs = set(children(fp,'attr')[0][1:]) if children(fp,'attr') else set()
        layer = children(fp,'layer')[0][1]
        require(layer=='F.Cu', f'A1 all-front assembly assumption changed: {ref} {layer}')
        require('dnp' not in attrs, f'Unexpected DNP needs explicit BOM policy: {ref}')
        result[ref] = {'value':fields.get('Value'), 'footprint':fp[1], 'attributes':attrs,
                       'mount':'SMD' if 'smd' in attrs else 'TH' if 'through_hole' in attrs else 'OTHER'}
    return result


def inventories():
    manifest = json.loads((BASE/'design-manifest.json').read_text())
    parts = json.loads((BASE/'parts-selection.json').read_text())['by_reference']
    components = {}
    for m in manifest:
        ref=m['reference']
        if ref.startswith('#'): continue
        require(ref not in components, f'Duplicate manifest reference {ref}')
        components[ref]=m
    require(set(components)==set(parts), 'Parts-selection and manifest reference sets differ')
    board = board_inventory()
    require(set(board)==set(components), 'PCB and manifest inventories differ')
    excluded = {ref for ref,p in parts.items() if p.get('purchasable') is False}
    require(excluded==FEATURES, f'Expected exactly the 11 bare-board features, got {sorted(excluded)}')
    assembly = set(components)-excluded
    require(len(assembly)==153 and len(components)==164, 'A1 requires 153 fitted + 11 PCB features')
    for ref,m in components.items():
        p=parts[ref]; b=board[ref]
        for key in ('mpn','manufacturer','footprint','source','notes'):
            require(bool(p.get(key)), f'Missing selection {key}: {ref}')
        require(m['mpn']==p['mpn'] and m['footprint']==p['footprint'], f'Selection/manifest mismatch: {ref}')
        require(b['footprint']==m['footprint'] and b['value']==m['value'], f'PCB value/footprint mismatch: {ref}')
        if ref in excluded:
            require(p['mpn']=='PCB_FEATURE_NOT_PURCHASED', f'Bare-board feature MPN: {ref}')
            require({'exclude_from_pos_files','exclude_from_bom'}<=b['attributes'], f'Feature assembly flags missing: {ref}')
        else:
            require('TBD' not in p['mpn'].upper() and not p['mpn'].startswith('PCB_'), f'Invalid fitted MPN: {ref}')
            require(not {'exclude_from_pos_files','exclude_from_bom'} & b['attributes'], f'Fitted component excluded: {ref}')
            require(b['mount'] in ('SMD','TH'), f'Mount type not specified: {ref}')
    return components,parts,board,assembly


def frozen_paths():
    paths = list(BASE.glob('*.kicad_sch')) + [PCB, BASE/'FarmMesh-Node.kicad_pro', BASE/'FarmMesh.kicad_sym',
        BASE/'sym-lib-table', BASE/'fp-lib-table', BASE/'design-manifest.json', BASE/'parts-selection.json',
        BASE/'BOM.csv', BASE/'gpio-pinmap.csv', BASE/'c5-pinmap.json']
    paths += list(BASE.glob('*.kicad_dru')) + list((BASE/'FarmMesh.pretty').glob('*'))
    paths += list((BASE/'scripts').glob('*.py')) + [p for p in (BASE/'third-party').rglob('*') if p.is_file()]
    return sorted(set(p for p in paths if p.is_file()))


def source_hashes():
    return {p.relative_to(BASE).as_posix():sha(p) for p in frozen_paths()}


def require_same_sources(expected):
    actual=source_hashes()
    require(actual==expected, 'Frozen source set or bytes changed; repeat verification and export before packaging')


def verify_prior_reports():
    cpath=BASE/'reports/connectivity-and-footprints.json'
    ppath=BASE/'reports/pcb-verification.json'
    c=json.loads(cpath.read_text()); p=json.loads(ppath.read_text())
    require(c.get('status')=='pass' and c.get('component_count')==164, 'Connectivity verification is missing/failed')
    for f in list(BASE.glob('*.kicad_sch'))+[BASE/'design-manifest.json',BASE/'reports/netlist.xml']:
        require(c.get('sha256',{}).get(f.relative_to(BASE).as_posix())==sha(f), f'Stale connectivity report: {f.name}')
    require(p.get('automated_status')=='pass', 'Independent PCB verification is missing/failed')
    for key,f in [('pcb',PCB),('manifest',BASE/'design-manifest.json'),('xml_netlist',BASE/'reports/netlist.xml')]:
        require(p.get('input_sha256',{}).get(key)==sha(f), f'Stale independent PCB report: {key}')
    require(bool(p.get('automated_checks')) and all(v.get('status')=='pass' for v in p['automated_checks'].values()), 'A PCB subcheck failed or is absent')
    share=Path(os.environ.get('KICAD_SHARE',str(CLI.parent.parent/'SharedSupport')))
    library_hashes=p['automated_checks'].get('library_pad_geometry',{}).get('library_file_sha256',{})
    require(bool(library_hashes),'Independent footprint hashes missing')
    for fid,digest in library_hashes.items():
        lib,name=fid.split(':',1)
        path=(BASE/'FarmMesh.pretty' if lib=='FarmMesh' else share/'footprints'/(lib+'.pretty'))/(name+'.kicad_mod')
        require(sha(path)==digest,f'Footprint library changed after review: {fid}')
    return [cpath,ppath,BASE/'reports/netlist.xml']


def all_payload_files(folder):
    files=[]
    for p in folder.rglob('*'):
        require(not p.is_symlink(), f'Package symlink is not permitted: {p}')
        if p.is_file():
            require(not re.search(r'(^|[-_])A0([._-]|$)',p.name,re.I), f'Old A0 artifact in package: {p}')
            files.append(p)
    return sorted(files)


def seal_manifest(folder, manifest):
    manifest['outputs']={p.relative_to(folder).as_posix():sha(p) for p in all_payload_files(folder)
                         if p.relative_to(folder).as_posix() not in {'manifest.json','SHA256SUMS'}}
    write_json(folder/'manifest.json',manifest)
    (folder/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.relative_to(folder).as_posix()}\n'
        for p in all_payload_files(folder) if p.relative_to(folder).as_posix()!='SHA256SUMS'))


def verify_closure(folder):
    manifest=json.loads((folder/'manifest.json').read_text())
    actual={p.relative_to(folder).as_posix():sha(p) for p in all_payload_files(folder)
            if p.relative_to(folder).as_posix() not in {'manifest.json','SHA256SUMS'}}
    require(actual==manifest['outputs'], 'Manifest closure failed: missing, added or changed package files')
    sums={line[66:]:line[:64] for line in (folder/'SHA256SUMS').read_text().splitlines()}
    expected={p.relative_to(folder).as_posix():sha(p) for p in all_payload_files(folder)
              if p.relative_to(folder).as_posix()!='SHA256SUMS'}
    require(sums==expected, 'SHA256SUMS closure failed')
    for name,digest in manifest.get('verification_report_sha256',{}).items():
        require(sha(folder/'audit'/name)==digest,f'Verification evidence mismatch: {name}')
        require(sha(folder/'native/reports'/name)==digest,f'Native verification evidence mismatch: {name}')
    for rel,digest in manifest['frozen_source_sha256'].items():
        require(sha(folder/'native'/rel)==digest, f'Native snapshot mismatch: {rel}')
    return manifest


def copy_documents(folder):
    for rel in DOCS:
        source=BASE/rel
        require(source.is_file(), f'Missing release documentation: {rel}')
        for subdir in ('documentation','native'):
            dest=folder/subdir/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)


def placements(raw, destination, components, board, assembly):
    with raw.open(newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f)
        require(reader.fieldnames==POSITION_FIELDS, f'Unknown KiCad 10 position CSV schema: {reader.fieldnames}')
        rows=list(reader)
    found={};seen=set()
    for row in rows:
        ref=row['Ref']; require(ref not in seen, f'Duplicate position {ref}');seen.add(ref)
        require(ref in assembly or ref in FEATURES, f'Unknown position {ref}')
        if ref in FEATURES: continue
        require(row['Val']==components[ref]['value'], f'Position value mismatch: {ref}')
        require(row['Package'] in [components[ref]['footprint'],components[ref]['footprint'].split(':',1)[1]], f'Position footprint mismatch: {ref}')
        require(row['Side'].lower() in ('top','front'), f'Unexpected placement side: {ref}')
        require(all(math.isfinite(float(row[k])) for k in ['PosX','PosY','Rot']), f'Non-finite coordinate: {ref}')
        found[ref]=row
    require(set(found)==assembly, f'Position fitted coverage mismatch: {sorted(assembly-set(found))}')
    smd={ref for ref in assembly if board[ref]['mount']=='SMD'}
    require(len(smd)==147,'A1 requires 147 SMD and 6 through-hole fitted components')
    for name, refs in [('placements-all.csv',assembly),('placements-smd.csv',smd)]:
        with (destination/name).open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=POSITION_FIELDS,lineterminator='\n');writer.writeheader()
            writer.writerows(found[ref] for ref in sorted(refs,key=natural))
    raw.unlink()
    write_json(destination/'placement-schema.json',{
        'schema':'KiCad 10 CSV','columns':POSITION_FIELDS,'units':'mm','origin':'KiCad absolute origin (0,0)',
        'axes':'X right; Y up. Negative Y values are expected for this board located below the KiCad origin.',
        'rotation':'KiCad front-side counterclockwise degrees; footprint origin, not guaranteed body centroid.',
        'side':'top/front; A1 has only front-side fitted parts','assembly_count':len(assembly),'smd_count':len(smd),
        'excluded_board_features':sorted(FEATURES,key=natural),'smd_policy':'Footprint SMD attribute; keep hybrid USB4105. Do not use --exclude-fp-th.',
        'fabricator_note':'Canonical engineering CSV, not a claim of JLC/LCSC turnkey part-number or rotation-library matching. Assembler must confirm importer, component rotation and body-centroid conventions.'})
    return len(smd)


def bom(destination, components, parts, assembly):
    groups={}
    for ref in assembly:
        m=components[ref];p=parts[ref]
        groups.setdefault((m['mpn'],p['manufacturer'],m['value'],m['footprint']),[]).append(ref)
    with (destination/'BOM-assembly.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['References','Quantity','Value','Manufacturer','MPN','Footprint','Notes'])
        for (mpn,maker,value,fp),refs in sorted(groups.items()):
            notes=' | '.join(sorted({parts[ref]['notes'] for ref in refs}))
            w.writerow([', '.join(sorted(refs,key=natural)),len(refs),value,maker,mpn,fp,notes])
    accessories=json.loads((BASE/'parts-selection.json').read_text())['accessories']
    with (destination/'BOM-accessories.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['Quantity','Manufacturer','MPN','Purpose','Notes','Source'])
        for part in accessories:
            require(part['quantity']>0 and part['mpn'] and 'TBD' not in part['mpn'],'Incomplete accessory selection')
            w.writerow([part['quantity'],part['manufacturer'],part['mpn'],part['purpose'],part['notes'],part['source']])


def export():
    before=source_hashes()
    components,parts,board,assembly=inventories()
    reports=verify_prior_reports();require_same_sources(before)
    report_hashes={p.name:sha(p) for p in reports}
    commands=[]
    def run(*args):
        command=[str(CLI),*map(str,args)]
        cp=subprocess.run(command,cwd=BASE,capture_output=True,text=True)
        commands.append({'argv':command,'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr})
        require(cp.returncode==0, 'KiCad failed: '+' '.join(command)+'\n'+cp.stdout+'\n'+cp.stderr[-4000:])
        return cp.stdout.strip()
    version=run('version');require(version.split('.')[0]=='10',f'KiCad 10 required, found {version}')
    with tempfile.TemporaryDirectory(prefix='.manufacturing-staging-',dir=BASE) as tmp:
        stage=Path(tmp)
        for name in ['gerber','drill','assembly','review','audit','native']:(stage/name).mkdir()
        run('sch','erc','--format','json','--severity-all','--exit-code-violations','-o',stage/'audit/erc.json',SCH)
        erc=json.loads((stage/'audit/erc.json').read_text())
        require('sheets' in erc and not any(s.get('violations') for s in erc['sheets']), 'ERC must have zero violations including exclusions')
        run('pcb','drc','--format','json','--severity-all','--exit-code-violations','--all-track-errors','--schematic-parity','-o',stage/'audit/drc.json',PCB)
        drc=json.loads((stage/'audit/drc.json').read_text())
        require(all(k in drc and not drc[k] for k in ['violations','unconnected_items','schematic_parity']), 'DRC/unconnected/parity must be zero')
        run('pcb','export','gerbers','--layers',','.join(LAYERS),'--no-protel-ext','--precision','6','--subtract-soldermask','-o',str(stage/'gerber')+'/',PCB)
        run('pcb','export','drill','--format','excellon','--drill-origin','absolute','--excellon-units','mm','--excellon-zeros-format','decimal','--excellon-oval-format','route','--excellon-separate-th','--generate-map','--map-format','pdf','--generate-report','--report-path',stage/'drill/drill-report.txt','-o',str(stage/'drill')+'/',PCB)
        raw=stage/'assembly/positions-raw.csv'
        run('pcb','export','pos','--format','csv','--units','mm','--side','both','--exclude-dnp','-o',raw,PCB)
        smd_count=placements(raw,stage/'assembly',components,board,assembly)
        bom(stage/'assembly',components,parts,assembly)
        run('pcb','export','ipcd356','-o',stage/'FarmMesh-Node-A1.ipc',PCB)
        run('sch','export','pdf','-o',stage/'review/FarmMesh-Node-A1.pdf',SCH)
        run('pcb','export','pdf','--layers','F.Fab,F.CrtYd,Edge.Cuts','--mode-single','--exclude-value','--no-property-popups','--black-and-white','--drill-shape-opt','0','--scale','2','-o',stage/'assembly/assembly-top.pdf',PCB)
        run('pcb','export','pdf','--layers',','.join(LAYERS),'--common-layers','Edge.Cuts','--mode-multipage','--no-property-popups','-o',stage/'review/FarmMesh-Node-A1-layers.pdf',PCB)
        require(len(list((stage/'gerber').glob('*.gbr')))==len(LAYERS),'Expected 11 Gerber layers')
        drills=sorted(p.name for p in (stage/'drill').glob('*.drl'))
        require(len(drills)==2 and any('-PTH.drl' in n for n in drills) and any('-NPTH.drl' in n for n in drills),'Expected separate PTH/NPTH drills')
        require(len(list((stage/'drill').glob('*.pdf')))==2,'Expected PTH/NPTH drill-map PDFs')
        for pdf in stage.rglob('*.pdf'):
            require(pdf.read_bytes().startswith(b'%PDF-'), f'Invalid PDF output: {pdf.name}')
        for rel,digest in before.items():
            dest=stage/'native'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(BASE/rel,dest)
            require(sha(dest)==digest, f'Native copy changed during export: {rel}')
        for report in reports:
            require(sha(report)==report_hashes[report.name],f'Verification report changed during export: {report.name}')
            shutil.copy2(report,stage/'audit'/report.name)
            (stage/'native/reports').mkdir(exist_ok=True)
            shutil.copy2(report,stage/'native/reports'/report.name)
        copy_documents(stage)
        (stage/'PACKAGE-CONTENTS.md').write_text('''# FarmMesh Node A1 package

Release authority/status: `documentation/RELEASE.md`. Sealing hashes does not approve fabrication.

- `gerber/`: 11 copper/mask/legend/paste/outline layers, with Gerber job file when emitted.
- `drill/`: separate PTH/NPTH Excellon files, drill report and two PDF drill maps.
- `assembly/BOM-assembly.csv`: 153 fitted components only. `placements-all.csv` has the same 153 references; `placements-smd.csv` contains 147 SMD components, including the hybrid USB connector. Read `placement-schema.json` before machine import.
- `assembly/BOM-accessories.csv`: eight separately selected antenna, cable and mating-harness part types with per-board quantities; these are not PCB placement rows.
- `review/`: PDFs generated from the frozen sources; explicit review evidence may be added during final sealing.
- `native/`: editable KiCad project, all eight schematics, local symbols/footprints/licenses, selected parts, engineering BOM, scripts and verification inputs. The engineering `native/BOM.csv` also lists 11 bare-board features; do not use it as the fitted assembly BOM.
- `audit/`: fresh ERC/DRC, prior independent verification bound to native hashes, and exact export commands.
- `documentation/`: manufacturing/first-board instructions and final review/status documents, mirrored into the native workspace for reproducibility.
- `manifest.json`: every payload SHA256 plus frozen source hashes. `SHA256SUMS` additionally hashes the manifest. The final ZIP checksum is external, avoiding self-referential hashes.

Reproduce with KiCad 10.0.5 (or re-review tool changes), the same library geometry and Python. In `native/`, regenerate `reports/netlist.xml`, run `scripts/verify_design.py` and `scripts/verify_pcb.py` using KiCad Python, then run `python3 scripts/export_manufacturing.py`. Review the new outputs, document authorized status separately, then run `python3 scripts/finalize_release.py` and `python3 scripts/finalize_release.py --check-only`. A changed native/BOM/parts/script hash requires a new export. CAD-generated timestamps can change a fresh export; sealing an unchanged payload produces a deterministic ZIP.
''',encoding='utf-8')
        write_json(stage/'audit/export-commands.json',commands)
        require_same_sources(before)
        m={'schema_version':2,'revision':'A1','status':'exported_pending_final_visual_and_expert_review',
           'exported_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kicad_version':version,
           'board_sha256':before[PCB.name],'frozen_source_sha256':before,'verification_report_sha256':report_hashes,
           'checks':{'erc_violations':0,'drc_violations':0,'unconnected':0,'schematic_parity':0,'independent_pcb_report':'pass'},
           'assembly_count':153,'board_feature_count':11,'smd_count':smd_count,
           'assembly_references':sorted(assembly,key=natural),'excluded_board_features':sorted(FEATURES,key=natural),
           'origin':'absolute for Gerber, drill and position exports; no auxiliary-origin offset',
           'sha_policy':'outputs covers every payload except manifest.json and SHA256SUMS. SHA256SUMS additionally covers manifest.json. Neither hashes itself; ZIP hash is external.'}
        seal_manifest(stage,m);verify_closure(stage)
        backup=None
        if OUT.exists():
            require(not OUT.is_symlink() and OUT.is_dir(),'Existing manufacturing path must be a real directory')
            backup=Path(tempfile.mkdtemp(prefix='.manufacturing-previous-',dir=BASE));backup.rmdir();OUT.rename(backup)
        try:stage.rename(OUT)
        except Exception:
            if backup is not None:backup.rename(OUT)
            raise
        print(json.dumps({'exported':str(OUT),'status':m['status'],'board_sha256':m['board_sha256'],'old_output_isolated_at':str(backup) if backup else None}))


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    try:export()
    except Exception as error:
        raise SystemExit(f'EXPORT ABORTED: {error}')


if __name__=='__main__':main()
