#!/usr/bin/env python3
"""Final mechanical keepouts and ground access, followed by external DRC.

This does not waive any check or remove signal routes. All modifications are
reported and must pass KiCad DRC before artifact export.
"""
from pathlib import Path
import json,math
import pcbnew as p
import wx
from ground_access import route as ground_access
from lx_keepout import patch as patch_lx_keepout
from finish_power_access import route as finish_power_access
from ground_stitching import route as ground_stitching
from fix_power_paste_clearance import patch as fix_power_paste_clearance
BASE=Path(__file__).resolve().parents[1]
app=wx.App(False);b=p.LoadBoard(str(BASE/'FarmMesh-Node.kicad_pcb'))
f={x.GetReference():x for x in b.GetFootprints()}
r={'power_access':finish_power_access(b)}
r['ground_access']=ground_access(b,f)
r['lx_keepout']=patch_lx_keepout(b)
for ref in ['H1','H2','H3','H4']:
    label='M3_HEAD_KEEP_OUT_'+ref
    existing=next((z for z in b.Zones() if z.GetZoneName()==label),None)
    if existing:
        existing.SetDoNotAllowPads(False)
        existing.SetDoNotAllowFootprints(False)
        continue
    xy=f[ref].GetPosition();x=p.ToMM(xy.x);y=p.ToMM(xy.y)
    z=p.ZONE(b);z.SetZoneName(label);z.SetIsRuleArea(True);ls=p.LSET();ls.AddLayer(p.F_Cu);ls.AddLayer(p.B_Cu);z.SetLayerSet(ls)
    z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(True);z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False)
    o=z.Outline();o.NewOutline()
    for j in range(48):
        a=2*math.pi*j/48;o.Append(p.FromMM(x+3.5*math.cos(a)),p.FromMM(y+3.5*math.sin(a)))
    b.Add(z)
r['paste_clearance']=fix_power_paste_clearance(b)
r['ground_stitching']=ground_stitching(b)
p.SaveBoard(str(BASE/'FarmMesh-Node.kicad_pcb'),b)
(BASE/'reports/ground-access.json').write_text(json.dumps(r,indent=2)+'\n')
(BASE/'reports/ground-stitching.json').write_text(json.dumps(r['ground_stitching'],indent=2)+'\n')
print(json.dumps(r))
