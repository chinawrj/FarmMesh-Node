#!/usr/bin/env python3
"""Offline DSN export/import for the remaining low-power signal routing.

A reviewed placement/critical-routing PCB is required. The seed remains the
source of power/USB/RP critical routes; this helper never changes the schematic.
"""
import argparse, json, shutil
from pathlib import Path
import pcbnew as p
import wx
BASE=Path(__file__).resolve().parents[1]
q=argparse.ArgumentParser();q.add_argument('mode',choices=['export','import']);q.add_argument('file');q.add_argument('--board',default=str(BASE/'FarmMesh-Node.kicad_pcb'));a=q.parse_args()
app=wx.App(False);b=p.LoadBoard(a.board)
if a.mode=='export':
    for t in b.GetTracks():t.SetLocked(True)
    for f in b.GetFootprints():f.SetLocked(True)
    # Export built-in default rules after loading project-managed constraints.
    b.BuildConnectivity()
    if not p.ExportSpecctraDSN(b,a.file):raise RuntimeError('DSN export failed')
else:
    # SES contains the router's additions but can omit every fixed seed item.
    # KiCad import replaces all tracks; retain the explicitly locked input.
    from merge_seed_routing import merge
    original=Path(a.board)
    backup=original.with_name(original.stem+'.before-ses.kicad_pcb')
    if backup.exists():raise RuntimeError('Refusing to replace existing SES backup: '+str(backup))
    shutil.copy2(original,backup)
    if not p.ImportSpecctraSES(b,a.file):raise RuntimeError('SES import failed')
    p.SaveBoard(a.board,b)
    audit=merge(backup,original,write=True)
    original.with_suffix('.ses-import.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps({'mode':a.mode,'file':a.file,'board':a.board}))
