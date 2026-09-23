#!/usr/bin/env python3
"""Build the A1 placement/critical-routing seed from the exported schematic netlist.

Run with the KiCad bundled Python. Full routing is a subsequent reviewed step;
this command replaces the PCB and must not be run on an edited release board.
"""
import json, math, os, xml.etree.ElementTree as ET
from pathlib import Path
import pcbnew as pcb
import wx
BASE=Path(__file__).resolve().parents[1]
SHARE=Path(os.environ.get('KICAD_SHARE',str(Path.home()/'Applications/KiCad/KiCad.app/Contents/SharedSupport')))
mm=pcb.FromMM
v=lambda x,y: pcb.VECTOR2I(mm(x),mm(y))
app=wx.App(False)
b=pcb.BOARD(); b.SetCopperLayerCount(4)
enabled=b.GetEnabledLayers();enabled.AddLayer(pcb.In1_Cu);enabled.AddLayer(pcb.In2_Cu);b.SetEnabledLayers(enabled)
d=b.GetDesignSettings();d.SetCopperLayerCount(4);d.SetBoardThickness(mm(1.6));d.m_TentViasFront=True;d.m_TentViasBack=True
d.m_MinClearance=mm(.1);d.m_TrackMinWidth=mm(.1);d.m_ViasMinSize=mm(.45);d.m_MinThroughDrill=mm(.2)
d.m_ViasMinAnnularWidth=mm(.125);d.m_CopperEdgeClearance=mm(.3);d.m_HoleClearance=mm(.2)
nc=d.m_NetSettings.GetDefaultNetclass();nc.SetClearance(mm(.15));nc.SetTrackWidth(mm(.15));nc.SetViaDiameter(mm(.45));nc.SetViaDrill(mm(.2));nc.SetDiffPairWidth(mm(.158));nc.SetDiffPairGap(mm(.2))
root=ET.parse(BASE/'reports/netlist.xml').getroot()
nets={};pin_nets={}
for n in root.findall('./nets/net'):
    name=n.get('name').replace(' / ', ' {slash} '); name=name.replace('/ADC', '{slash}ADC') if name.startswith('unconnected-') else name; ni=pcb.NETINFO_ITEM(b,name);b.Add(ni);nets[name]=ni
    for nd in n.findall('node'):pin_nets[(nd.get('ref'),nd.get('pin'))]=ni
by_short={n.rsplit('/',1)[-1]:ni for n,ni in nets.items()}
footprints={}
for c in root.findall('./components/comp'):
    ref=c.get('ref'); fid=c.findtext('footprint')
    if not fid:continue
    lib,name=fid.split(':',1); libpath=BASE/'FarmMesh.pretty' if lib=='FarmMesh' else SHARE/'footprints'/f'{lib}.pretty'
    f=pcb.FootprintLoad(str(libpath),name)
    if not f:raise RuntimeError(f'Cannot load {fid}')
    f.SetReference(ref);f.SetValue(c.findtext('value'));f.SetField('Datasheet',c.findtext('datasheet') or '');f.SetField('Description',c.findtext('description') or '');f.SetFPID(pcb.LIB_ID(lib,name))
    sp=c.find('sheetpath');path=sp.get('tstamps')+c.findtext('tstamps')
    f.SetPath(pcb.KIID_PATH(path));f.SetSheetname(sp.get('names',''))
    f.SetSheetfile(c.findtext('source')) if c.findtext('source') else None
    b.Add(f);footprints[ref]=f
    for p in f.Pads():
        if (ref,p.GetNumber()) in pin_nets:p.SetNet(pin_nets[(ref,p.GetNumber())])
    f.Value().SetVisible(False)
    for fld in f.GetFields():
        if fld.GetName() not in ['Reference','Value']:fld.SetVisible(False)
    f.Reference().SetTextSize(v(.8,.8));f.Reference().SetTextThickness(mm(.12))
    if ref.startswith(('TP','H')):f.SetExcludedFromBOM(True);f.SetExcludedFromPosFiles(True)
    for fld in c.findall('./fields/field'):
        if fld.get('name')=='MPN':f.SetField('MPN',fld.text)

    for fld in f.GetFields():
        if fld.GetName() not in ['Reference','Value']:fld.SetVisible(False)

placements={
'H1':(5,5,0),'H2':(95,5,0),'H3':(5,95,0),'H4':(95,95,0),
'U201':(20,20,90),'U301':(20,80,180),'U401':(80,80,270),
'J102':(50,4,180),'D101':(50,12,270),'R108':(44,10.5,90),'R109':(56,10.5,90),
'U103':(50,19,180),'U104':(59,18,0),'R114':(63,17,90),'R115':(63,20.5,90),'R116':(55,13,0),
'C128':(49.5,21.6,0),'C129':(59,14,0),'C130':(59,22,0),
'R112':(58,24,0),'R113':(58,26,0),'C126':(61,26,0),'C127':(58,7,90),
'J101':(63,35,0),'SW101':(31,44,90),'SW102':(65,8,0),'R104':(63,13,0),
'J1':(88,40,0),'F1':(92,34,90),'Q1':(90,28,0),'R1':(94,29,90),'J2':(95,17,0),
'U1':(80,27,0),'L1':(80,17,0),'C1':(84,22,90),'C2':(76,22,90),
'C3':(86,26,90),'C4':(88,26,90),'C5':(85.5,30,90),'C6':(92,22,90),
'C7':(69,27,0),'C8':(74,26,90),'C9':(74,29,90),'C11':(82,34,90),'D1':(83,37,0),
'R2':(72,32,90),'R3':(74,33,90),'R4':(76,34,90),'C10':(76,37,90),
'R5':(84,34,90),'R6':(70,36,90),'R7':(88,36,90),'R8':(90,36,90),'C12':(86,37,90),
'TP1':(93,48,0),'TP2':(66,26,0),'TP3':(70,42,0),
'TP101':(40,64,0),'TP102':(60,60,0),'TP103':(61,30,0),'TP104':(68,45,0),
}
geom=json.loads((BASE/'third-party/raspberry-pi/rp2350b-reference-geometry.json').read_text())
for c in geom['components']:
    for j,ref in enumerate(c['our_refs']):
        x,y=c['xy_target_rp50_mm'];placements[ref]=(x,y+j*1.2,c['angle_deg'])
placements.update({'R103':(39.7,32.6,0),'C124':(53.1,58.3,-90),'C120':(49,38.8,90),'C116':(57.5,44.5,0)})
try:
    from radio_placement import placements as radio_placements
    placements.update(radio_placements())
except ImportError:pass
from power_placement import placements as power_placements
placements.update(power_placements())
# Driver resistors at RP. Stagger outward by group to escape QFN pitch.
for group,prefix in enumerate([200,300,400]):
    for k,j in enumerate([6,7,8,9,11]):
        if group==0:xy=(39.5-(k%2)*2.2,46.8+k*1.3,0)
        elif group==1:xy=(38.5+k*2.2,58.5+(k%2)*1.6,90)
        else:xy=(62.0+(k%2)*2,54-k*1.3,180)
        placements[f'R{prefix+10+j}']=xy
    placements[f'R{prefix+4}']=[(38.5,44,0),(37.5,56,0),(63,56,0)][group]
# Missing placements are deliberately staged off-board, and reported.
missing=[]
for i,(ref,f) in enumerate(footprints.items()):
    if ref not in placements:placements[ref]=(110+(i%10)*10,10+(i//10)*10,0);missing.append(ref)
    x,y,a=placements[ref];f.SetOrientationDegrees(a);f.SetPosition(v(x,y))
    # Keep text horizontal for readable assembly/silkscreen review.
    f.Reference().SetTextAngle(pcb.EDA_ANGLE(0,pcb.DEGREES_T))
for a,z in [((0,0),(100,0)),((100,0),(100,100)),((100,100),(0,100)),((0,100),(0,0))]:
    s=pcb.PCB_SHAPE();s.SetShape(pcb.SHAPE_T_SEGMENT);s.SetStart(v(*a));s.SetEnd(v(*z));s.SetWidth(mm(.05));s.SetLayer(pcb.Edge_Cuts);b.Add(s)

def track(net,points,width=.15,layer=pcb.F_Cu):
    for a,z in zip(points,points[1:]):
        if a==z:continue
        t=pcb.PCB_TRACK(b);t.SetStart(v(*a));t.SetEnd(v(*z));t.SetWidth(mm(width));t.SetLayer(layer);t.SetNet(by_short[net]);b.Add(t)
    return t

def via(net,x,y,diam=.6,drill=.3):
    t=pcb.PCB_VIA(b);t.SetPosition(v(x,y));t.SetWidth(mm(diam));t.SetDrill(mm(drill));t.SetViaType(pcb.VIATYPE_THROUGH);t.SetLayerPair(pcb.F_Cu,pcb.B_Cu);t.SetNet(by_short[net]);b.Add(t);return t

def plane(net,layer,poly,priority=0,keepout=False):
    z=pcb.ZONE(b);z.SetLayer(layer);z.SetNet(by_short[net]);z.SetLocalClearance(mm(.15));z.SetMinThickness(mm(.15));z.SetPadConnection(pcb.ZONE_CONNECTION_FULL);z.SetAssignedPriority(priority)
    if keepout:z.SetIsRuleArea(True);z.SetDoNotAllowZoneFills(True)
    o=z.Outline();o.NewOutline()
    for x,y in poly:o.Append(mm(x),mm(y))
    b.Add(z);return z
from rp_routing import route as rp_route
rp_routing=rp_route(b,footprints,by_short)
from usb_routing import route as usb_route
usb_route(b,footprints,by_short)
from radio_placement import route as radio_route
radio_routing=radio_route(b,footprints,by_short)
from power_placement import route as power_route
power_routing=power_route(b,footprints,by_short)
from power_tree import route as tree_route
power_tree=tree_route(b,footprints,by_short,rp_feed=(57.3,36))
(BASE/'reports/power-distribution.json').write_text(json.dumps(power_tree,indent=2)+'\n')
# QFN EP ground via ring avoids holes in stencil apertures.
for x,y in [(-2.1,-1.1),(-2.1,1.1),(2.1,-1.1),(2.1,1.1),(-1.1,-2.1),(0,-2.2),(-1.1,2.1),(1.7,2.2)]:via('GND',50+x,50+y)
# Continuous inner ground references except the local RP VREG_LX keepout.
for layer in [pcb.In1_Cu,pcb.In2_Cu]:plane('GND',layer,[(.3,.3),(99.7,.3),(99.7,99.7),(.3,99.7)])
plane('GND',pcb.F_Cu,[(47.6,47.6),(52.4,47.6),(52.4,52.4),(47.6,52.4)],1)
# RP2350 datasheet 6.3.8 / Fig 24: clear L2 below the complete LX copper,
# including the narrow neck and pad 63 down to y=45.475 mm.
lx_keepout=plane('GND',pcb.In1_Cu,[(52.2,39.9),(54.3,39.9),(54.3,42.4),(53.6,43.2),(53.3,43.2),(53.3,45.65),(52.7,45.65),(52.7,43.2),(52.2,43.2)],keepout=True)
lx_keepout.SetZoneName('RP_LX_L2_COPPER_KEEPOUT')
# Known quiet areas receive stitching after final routing, not arbitrary vias across signal escapes.
b.SetFileName(str(BASE/'FarmMesh-Node.kicad_pcb'));pcb.SaveBoard(b.GetFileName(),b)
# JLC04161H-3313 vendor nominal stackup. Finished overall board is 1.6 mm;
# individual nominal core/prepreg/copper dimensions are retained verbatim.
stackup='\t\t(stackup\n (layer "F.SilkS" (type "Top Silk Screen"))\n (layer "F.Paste" (type "Top Solder Paste"))\n (layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))\n (layer "F.Cu" (type "copper") (thickness 0.035))\n (layer "dielectric 1" (type "prepreg") (thickness 0.0994) (material "JLC 3313") (epsilon_r 4.1))\n (layer "In1.Cu" (type "copper") (thickness 0.0152))\n (layer "dielectric 2" (type "core") (thickness 1.265) (material "JLC core") (epsilon_r 4.42))\n (layer "In2.Cu" (type "copper") (thickness 0.0152))\n (layer "dielectric 3" (type "prepreg") (thickness 0.0994) (material "JLC 3313") (epsilon_r 4.1))\n (layer "B.Cu" (type "copper") (thickness 0.035))\n (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))\n (layer "B.Paste" (type "Bottom Solder Paste"))\n (layer "B.SilkS" (type "Bottom Silk Screen"))\n (copper_finish "ENIG") (dielectric_constraints yes)\n )\n'
boardpath=Path(b.GetFileName());raw=boardpath.read_text();raw=raw.replace('\t(setup\n','\t(setup\n'+stackup,1);boardpath.write_text(raw)
report={'stage' :'placement_seed_not_for_fabrication','footprint_count':len(footprints),'net_count':len(nets),'missing_placements':missing,'layers':4,'size_mm':[100,100]}
(BASE/'reports/pcb-build.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
