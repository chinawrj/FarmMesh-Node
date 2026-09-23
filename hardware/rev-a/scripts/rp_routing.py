#!/usr/bin/env python3
"""RP2350B local routing adapted from official R4/S1 reference geometry.

route(board, footprints, nets=None) adds copper to the supplied in-memory board.
Nets may be a short-name/full-name map; actual pad NetInfo is authoritative.
No PCB is loaded/saved. External USB, GPIO and debug wiring remain caller-owned.
U101 must be (50,50), 0 degrees; C120 must be (49,38.8), 90 degrees.

The front-side buck polygons reproduce the official compact current loops.
A small B.Cu 1V1 island replaces the source F.Cu central distribution polygon
so the target QFN EP can have an uninterrupted F.Cu ground return. L2/L3 GND
and the top-layer EP ground/via ring are caller-owned, as is the LX keepout.
"""
import json
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
FEED_VIAS=((56.5,36.0),(57.3,36.0))


def route(board, footprints, nets=None):
    import pcbnew as p
    mm=p.FromMM
    V=lambda xy:p.VECTOR2I(mm(xy[0]),mm(xy[1]))
    xy=lambda q:(p.ToMM(q.x),p.ToMM(q.y))
    netmap={pad.GetNetname().rsplit('/',1)[-1]:pad.GetNet() for f in footprints.values() for pad in f.Pads() if pad.GetNetCode()}
    def pad(ref,num):return next(q for q in footprints[ref].Pads() if q.GetNumber()==str(num))
    def pos(ref,num):return xy(pad(ref,num).GetPosition())
    if abs(xy(footprints['U101'].GetPosition())[0]-50)>.001 or abs(xy(footprints['U101'].GetPosition())[1]-50)>.001:raise ValueError('RP routing requires U101 at (50,50)')
    if any(abs(a-b)>.001 for a,b in zip(xy(footprints['C120'].GetPosition()),(49,38.8))):raise ValueError('Set C120 to (49,38.8), 90 degrees before routing')
    count={'segments':0,'vias':0,'zones':0}
    # Exact-geometry idempotence permits safe repeated calls while iterating.
    existing=set()
    def key(t):
        if isinstance(t,p.PCB_VIA):return ('v',t.GetNetCode(),tuple(t.GetPosition()),t.GetWidth(p.F_Cu),t.GetDrill())
        return ('t',t.GetNetCode(),t.GetLayer(),tuple(sorted((tuple(t.GetStart()),tuple(t.GetEnd())))),t.GetWidth())
    for t in board.GetTracks():existing.add(key(t))
    def add(t,kind):
        k=key(t)
        if k not in existing:board.Add(t);existing.add(k);count[kind]+=1
    def line(net,points,w=.15,layer=p.F_Cu):
        for a,b in zip(points,points[1:]):
            if a==b:continue
            t=p.PCB_TRACK(board);t.SetStart(V(a));t.SetEnd(V(b));t.SetWidth(mm(w));t.SetLayer(layer);t.SetNet(netmap[net]);add(t,'segments')
    def via(net,point,d=.6,dr=.3):
        t=p.PCB_VIA(board);t.SetPosition(V(point));t.SetWidth(mm(d));t.SetDrill(mm(dr));t.SetViaType(p.VIATYPE_THROUGH);t.SetLayerPair(p.F_Cu,p.B_Cu);t.SetNet(netmap[net]);t.SetFrontTentingMode(p.TENTING_MODE_TENTED);t.SetBackTentingMode(p.TENTING_MODE_TENTED);add(t,'vias')
    def zone(label,net,layer,points,priority):
        if any(z.GetZoneName()==label for z in board.Zones()):return
        z=p.ZONE(board);z.SetZoneName(label);z.SetLayer(layer);z.SetNet(netmap[net]);z.SetLocalClearance(mm(.15));z.SetMinThickness(mm(.1));z.SetPadConnection(p.ZONE_CONNECTION_FULL);z.SetAssignedPriority(priority)
        o=z.Outline();o.NewOutline()
        for a,b in points:o.Append(mm(a),mm(b))
        board.Add(z);count['zones']+=1
    geom=json.loads((BASE/'third-party/raspberry-pi/rp2350b-reference-geometry.json').read_text())
    critical={'CORE_1V1','VREG_A','VREG_LX','XIN','XOUT','XTAL_OUT','RP_USB_DP','RP_USB_DM'}
    for t in geom['routing']:
        if not t['spatial_candidate']:continue
        if t['target_net'] not in critical:
            if not(t['target_net']=='+3V3' and t['kind']=='segment' and t['layer']=='F.Cu' and all(41<=pt[0]<=59 and 40<=pt[1]<=59 for pt in [t['start_target_rp50_mm'],t['end_target_rp50_mm']])):continue
        if t['target_net']=='+3V3' and t['kind']=='segment' and t['width_mm']==.2 and tuple(t['end_target_rp50_mm']) in {(51,45.9),(45.9,47.8),(49.4,54.1),(47.8,45.9),(45.9,51.8),(47.4,54.1),(50.6,45.9),(53.8,50.2)}:continue
        if t['target_net']=='CORE_1V1' and t['kind']=='via' and tuple(t['xy_target_rp50_mm']) in {(52.3,49.8),(51.7,47.8),(47.8,49.8),(50.8,52.3)}:continue
        if t['kind']=='segment':line(t['target_net'],[t['start_target_rp50_mm'],t['end_target_rp50_mm']],t['width_mm'],board.GetLayerID(t['layer']))
        else:via(t['target_net'],t['xy_target_rp50_mm'],max(.45,t['diameter_mm']),max(.2,t['drill_mm']))
    # Buck current-loop polygons: translated verbatim by (-50,-50) from reference.
    zone('RP_BUCK_1V1','CORE_1V1',p.F_Cu,[(52.65,43.25),(52.65,40.5),(51.95,40.5),(51.95,42.3),(52.25,42.6),(52.25,42.75),(52.05,42.75),(51.85,42.55),(51.65,42.55),(51.4,42.8),(51.4,43.45),(51.6,43.65),(51.8,43.65),(52,43.45),(52.55,43.45),(52.55,43.25)],6)
    zone('RP_BUCK_LX','VREG_LX',p.F_Cu,[(52.9,45.4),(52.9,44.6),(52.85,44.55),(52.85,42.4),(53.35,41.9),(53.35,40.5),(54.05,40.5),(54.05,42.2),(53.75,42.5),(53.3,42.5),(53.15,42.65),(53.15,44.55),(53.1,44.6),(53.1,45.4)],5)
    zone('RP_BUCK_VIN','+3V3',p.F_Cu,[(52.5,45.85),(52.5,44.45),(52.25,44.2),(52.25,43.7),(52.7,43.7),(52.7,45.85)],7)
    zone('RP_BUCK_PGND','GND',p.F_Cu,[(53.3,45.4),(53.3,43.7),(53.45,43.7),(53.45,43.25),(53.3,43.25),(53.3,42.75),(54.1,42.75),(54.4,43.05),(54.4,43.8),(53.5,44.7),(53.5,45.4)],4)
    for point in [(54.1,43.25),(54.1,43.85)]:via('GND',point,.6,.25)
    # CFILT gets a separate, short ground path, not a PGND daisy chain.
    line('GND',[pos('C101',2),(55.65,44.43)],.25);via('GND',(55.65,44.43),.5,.25)
    zone('RP_CORE_DISTRIBUTION','CORE_1V1',p.B_Cu,[(47.4,47.4),(52.6,47.4),(52.6,52.6),(47.4,52.6)],3)
    line('CORE_1V1',[pos('C124',1),(52.6,57.525),(51.4,57.82)],.35)
    # Explicit pad-to-ground-via branches (no open through holes in SMD pads).
    grounds={
      'C104':(44.9,32.8),'C105':(47.4,60.42),'C106':(52.8,60.42),
      'C110':(40.785,47.1),'C111':(40.8,52.2),'C112':(44.1,57.2755),
      'C113':(48.7,59.6),'C114':(58.715,54.5),'C115':(59.22,50.5),
      'C116':(58.8,44.3),'C117':(43,41.9),'C118':(58.8,45.2),
      'C119':(49,40.05),'C120':(49,37.65),'C121':(40.78,49.8),
      'C122':(52.2,58.82),'C123':(59.22,49.5),'C124':(54.1,59.3)}
    for ref,point in grounds.items():line('GND',[pos(ref,2),point],.15);via('GND',point)
    line('GND',[pos('U102',4),(39.4,40)],.2);via('GND',(39.4,40))
    for num,point in [(2,(52.7,64.8)),(4,(47.3,63.2))]:line('GND',[pos('Y101',num),point],.25);via('GND',point)
    zone('RP_CRYSTAL_GND','GND',p.F_Cu,[(46.6,59.4),(53.5,59.4),(53.8,59.7),(53.8,67.2),(46.6,67.2)],2)
    # Only the populated front flash path; no optional U4 bottom-layer branches.
    qs={
      'QSPI_IO0':[(49.4,45.1035),(49.4,44),(46.6,41.2),pos('U102',5)],
      'QSPI_IO1':[(48.6,45.1035),(48.6,44.2),(45.1,40.7),(38.95,40.7),(38,39.75),(38,37.6),(39.035,36.565),pos('U102',2)],
      'QSPI_IO2':[(49,45.1035),(49,44.1),(45,40.1),(42.6,40.1),(40.7,38.2),(40.335,37.835),pos('U102',3)],
      'QSPI_IO3':[(50.2,45.1035),(50.2,43.8),(48.4,42),(48.4,37.7),(47.265,36.565),pos('U102',7)],
      'QSPI_CLK':[(49.8,45.1035),(49.8,43.9),(47.8,41.9),(47.8,38.5),(47.135,37.835),pos('U102',6)],
      'QSPI_CS':[(48.2,45.1035),(48.2,44.3),(45.2,41.3),(38.7,41.3),(37.4,40),(37.4,33.52),(38.32,32.6),pos('R103',1)]}
    for net,points in qs.items():line(net,points)
    line('QSPI_CS',[pos('R103',1),(39.4125,32.8225),pos('U102',1)],.15)
    # Replaces absent R10 and avoids R103 BOOT_BUTTON pad under the source branch.
    line('QSPI_CS',[pos('U102',1),(39.4125,34),(42.4,34),pos('R102',2)],.15)
    # Local +3V3 B.Cu perimeter distribution, outside the 1V1 island/arms.
    ring=[(41.8,34.2),(61,34.2),(61,61.4),(41.8,61.4),(41.8,34.2)]
    line('+3V3',ring,.4,p.B_Cu)
    branches=[
      ('C110',(43.25,47.1),[(43.25,47.1),(41.8,47.1)]),
      ('C111',(43.25,52.2),[(43.25,52.2),(41.8,52.2)]),
      ('C112',(45.5,57.5),[(45.5,57.5),(45.5,61.4)]),
      ('C113',(48.7,57.1),[(48.7,57.1),(45.5,57.1),(45.5,57.5)]),
      ('C114',(56.2,54.5),[(56.2,54.5),(56.2,55.6),(61,55.6)]),
      ('C115',(57,51.4),[(57,51.4),(61,51.4)]),
      ('C116',(56.8,43.4),[(56.8,43.4),(61,43.4)]),
      ('C117',(44.68,42.8),[(44.68,42.8),(41.8,42.8)]),
      ('C119',(49.2,42.15),[(49.2,42.15),(50.2,41.15),(50.2,34.2)])]
    for ref,point,path in branches:
        line('+3V3',[pos(ref,1),point],.15);via('+3V3',point,.45 if ref=='C119' else .6,.2 if ref=='C119' else .3);line('+3V3',path,.4,p.B_Cu)
    line('+3V3',[pos('C116',1),pos('C118',1)],.2)
    line('+3V3',[pos('U101',60),(55.4,46.2),pos('C116',1)],.15)
    # Keep the USB corridor x50/50.358 unobstructed; this short decap feed runs
    # in the verified 0.35 mm corridor between C120 and DP, then joins flash VCC.
    line('+3V3',[pos('C120',1),(49.65,39.28),(49.65,35.295),pos('U102',8)],.15)
    line('+3V3',[pos('U102',8),(46.5875,32.9075),pos('C104',1)],.3)
    via('+3V3',(47.6,32.83));line('+3V3',[pos('C104',1),(47.6,32.83)],.3);line('+3V3',[(47.6,32.83),(47.6,34.2)],.4,p.B_Cu)
    via('+3V3',(43.25,31.79));line('+3V3',[pos('R102',1),(43.25,31.79)],.2);line('+3V3',[(43.25,31.79),(43.25,34.2)],.4,p.B_Cu)
    # Buck/AVDD input is fed separately from the digital decap exits.
    via('+3V3',(55.8,40.4));line('+3V3',[pos('R101',1),(55.8,40.54),(55.8,40.4)],.3);line('+3V3',[(55.8,40.4),(55.8,34.2)],.6,p.B_Cu)
    via('+3V3',(52.6,46.4));line('+3V3',[(52.6,45.9),(52.6,46.4)],.3);line('+3V3',[(52.6,46.4),(54.9,46.4),(54.9,40.4),(55.8,40.4)],.6,p.B_Cu)
    for point in FEED_VIAS:via('+3V3',point);line('+3V3',[point,(point[0],34.2)],.8,p.B_Cu)
    line('+3V3',list(FEED_VIAS),.8,p.F_Cu)
    count.update({'rp_feed_vias_mm':[list(q) for q in FEED_VIAS], 'rp_feed_diameter_drill_mm':[.6,.3], 'core_distribution_layer':'B.Cu','status':'requires whole-board DRC and hardware validation'})
    return count
