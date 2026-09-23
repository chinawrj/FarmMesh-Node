#!/usr/bin/env python3
"""Place readable prototype silkscreen; every reference remains in F.Fab.

Dense R/C identifiers are on the assembly drawing, with major interfaces and
polarity marks on the board. Do not suppress copper DRC findings here.
"""
from pathlib import Path
import pcbnew as p
import wx
BASE=Path(__file__).resolve().parents[1]
app=wx.App(False);b=p.LoadBoard(str(BASE/'FarmMesh-Node.kicad_pcb'))
v=lambda x,y:p.VECTOR2I(p.FromMM(x),p.FromMM(y))
def box(q):
    bb=q.GetBoundingBox();a,z=bb.GetOrigin(),bb.GetEnd();return [p.ToMM(a.x),p.ToMM(a.y),p.ToMM(z.x),p.ToMM(z.y)]
def touch(a,b,gap=0):return not(a[2]+gap<b[0] or a[0]-gap>b[2] or a[3]+gap<b[1] or a[1]-gap>b[3])
obstacles=[]
for f in b.GetFootprints():
    for pad in f.Pads():
        if pad.IsOnLayer(p.F_Mask) or pad.GetDrillSize().x:obstacles.append(box(pad))
# Dense nonpolar passive identifiers are shown on the assembly drawing.
# Preserve all library copper, mask, paste and polarity/outline graphics.
for f in b.GetFootprints():
    ref=f.GetReference();dense=ref.startswith('R') or ref.startswith('C') and 'CP_Elec' not in str(f.GetFPID().GetLibItemName())
    if dense:
        f.Reference().SetVisible(False)
    else:f.Reference().SetVisible(True)
occupied=[]
for f in b.GetFootprints():
    for g in f.GraphicalItems():
        if g.GetLayer()==p.F_SilkS:
            gb=box(g)
            occupied.append(gb)
# Candidate locations are outside component pad bounds, nearest-first.
for f in sorted(b.GetFootprints(),key=lambda f:f.GetReference()):
    t=f.Reference()
    if not t.IsVisible():continue
    t.SetTextAngle(p.EDA_ANGLE(0,p.DEGREES_T));t.SetTextSize(v(.85,.85));t.SetTextThickness(p.FromMM(.12))
    x,y=p.ToMM(f.GetPosition().x),p.ToMM(f.GetPosition().y)
    pads=[box(q) for q in f.Pads()]
    if not pads:continue
    left=min(q[0] for q in pads);right=max(q[2] for q in pads);top=min(q[1] for q in pads);bottom=max(q[3] for q in pads)
    width=.85*.8*len(t.GetText());height=.85
    candidates=[]
    for d in [1.1,1.8,2.6,3.5,5.0]:
        candidates.extend([(x,top-d),(x,bottom+d),(left-width/2-d,y),(right+width/2+d,y)])
    placed=False
    for xx,yy in candidates:
        t.SetPosition(v(xx,yy));bb=box(t)
        if bb[0]<.4 or bb[1]<.4 or bb[2]>99.6 or bb[3]>99.6:continue
        if any(touch(bb,q,.13) for q in obstacles+occupied):continue
        occupied.append(bb);placed=True;break
    if not placed:t.SetVisible(False)
# Product markings occupy deliberately open central/bottom areas.
for txt,x,y,size in [('FarmMesh Node  A1',50,83,1.45),('RP2350B + 3 x C5',50,86,1.0),('1S Li-ion  |  No charger',50,89,1.0),('USB: battery required',50,28,0.8)]:
    if any(isinstance(d,p.PCB_TEXT) and d.GetText()==txt for d in b.GetDrawings()):continue
    t=p.PCB_TEXT(b);t.SetText(txt);t.SetPosition(v(x,y));t.SetTextSize(v(size,size));t.SetTextThickness(p.FromMM(.13));t.SetLayer(p.F_SilkS)
    bb=box(t)
    if any(touch(bb,q,.13) for q in obstacles+occupied):continue
    b.Add(t);occupied.append(bb)
p.SaveBoard(str(BASE/'FarmMesh-Node.kicad_pcb'),b)
