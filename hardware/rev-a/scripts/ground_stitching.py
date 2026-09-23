"""Conservative nearby GND stitching for signal through-via layer transitions.

route(board, allow_small_fallback=True) adds tented 0.6/0.3 mm through vias;
only if those do not fit, it tries the fabrication-approved 0.45/0.2 mm size.
It never loads/saves/refills a PCB, moves copper, or deletes existing routes.
A <=2 mm plated-GND neighbor is a review heuristic, not an SI certification.
Refill all zones and obtain KiCad DRC=0 before accepting any additions.
"""
import collections
import math

# Supply/switch-node vias are not classified as signal transitions here.
POWER_NETS = {'GND', '+3V3', 'CORE_1V1', 'BAT_PLUS', 'BAT_FUSED',
              'VBAT_PROTECTED', 'VREG_A', 'VREG_LX', 'REG_VCC',
              'SW1', 'SW2', 'BST1', 'BST2', 'USB_VBUS', 'VBUS'}
DIAMETER = .6
DRILL = .3
NEIGHBOR_DISTANCE = 2.0
COPPER_CLEARANCE = .17
HOLE_EDGE_CLEARANCE = .21
PAD_PASTE_CLEARANCE = .05


def route(board, allow_small_fallback=True):
    import pcbnew as p
    mm=p.FromMM
    xy=lambda q:(p.ToMM(q.x),p.ToMM(q.y))
    V=lambda q:p.VECTOR2I(mm(q[0]),mm(q[1]))
    layers=(p.F_Cu,p.In1_Cu,p.In2_Cu,p.B_Cu)
    footprints=list(board.GetFootprints())
    pads=[q for f in footprints for q in f.Pads()]
    ground_net=next((q.GetNet() for q in pads if q.GetNetname()=='GND'),None)
    if ground_net is None:raise ValueError('The board must contain a GND net')
    if board.GetCopperLayerCount()!=4:raise ValueError('Ground stitching is reviewed only for the four-layer A1 board')
    def bounds(item):
        box=item.GetBoundingBox()
        return (p.ToMM(box.GetLeft()),p.ToMM(box.GetTop()),p.ToMM(box.GetRight()),p.ToMM(box.GetBottom()))
    def rectdist(point,rect):
        return math.hypot(max(rect[0]-point[0],0,point[0]-rect[2]),
                          max(rect[1]-point[1],0,point[1]-rect[3]))
    def segdist(point,a,z):
        dx=z[0]-a[0];dy=z[1]-a[1];den=dx*dx+dy*dy
        t=max(0,min(1,((point[0]-a[0])*dx+(point[1]-a[1])*dy)/den)) if den else 0
        return math.hypot(point[0]-a[0]-t*dx,point[1]-a[1]-t*dy)
    # Spatial bins make dense candidate search practical without relaxing geometry.
    cell=2.0
    bins=collections.defaultdict(list)
    records=[]
    def record(kind,box,margin,**data):
        index=len(records)
        records.append(dict(kind=kind,box=box,margin=margin,**data))
        for xx in range(math.floor((box[0]-margin)/cell),math.floor((box[2]+margin)/cell)+1):
            for yy in range(math.floor((box[1]-margin)/cell),math.floor((box[3]+margin)/cell)+1):
                bins[(xx,yy)].append(index)
    def hole_record(center,a,z,radius,label):
        box=(min(a[0],z[0])-radius,min(a[1],z[1])-radius,
             max(a[0],z[0])+radius,max(a[1],z[1])+radius)
        record('hole',box,DRILL/2+HOLE_EDGE_CLEARANCE,a=a,z=z,radius=radius,label=label)
    grounds=[]
    for f in footprints:
        for q in f.Pads():
            # Bounding rectangles deliberately overestimate rounded/custom pads.
            # Even same-net copper/paste pads must not be under the new annulus.
            on_copper=any(q.IsOnLayer(layer) for layer in layers) and q.GetAttribute()!=p.PAD_ATTRIB_NPTH
            paste_growth=0.0
            for paste_layer in (p.F_Paste,p.B_Paste):
                if q.IsOnLayer(paste_layer):
                    expansion=q.GetSolderPasteMargin(paste_layer)
                    paste_growth=max(paste_growth,p.ToMM(expansion.x),p.ToMM(expansion.y))
            pad_gap=max(PAD_PASTE_CLEARANCE+paste_growth,
                        COPPER_CLEARANCE if on_copper and q.GetNetname()!='GND' else 0)
            margin=DIAMETER/2+pad_gap
            record('pad_or_paste',bounds(q),margin,label=f.GetReference()+'.'+q.GetNumber())
            drill=q.GetDrillSize()
            if drill.x or drill.y:
                center=xy(q.GetPosition());sx=p.ToMM(drill.x);sy=p.ToMM(drill.y)
                angle=math.radians(q.GetOrientationDegrees())
                dx=max(0,sx-sy)/2;dy=max(0,sy-sx)/2
                rx=dx*math.cos(angle)+dy*math.sin(angle);ry=-dx*math.sin(angle)+dy*math.cos(angle)
                a=(center[0]-rx,center[1]-ry);z=(center[0]+rx,center[1]+ry)
                hole_record(center,a,z,min(sx,sy)/2,f.GetReference()+'.'+q.GetNumber())
                if q.GetAttribute()==p.PAD_ATTRIB_PTH and q.GetNetname()=='GND':
                    grounds.append({'xy':center,'type':'plated_ground_pad','reference':f.GetReference(),'pad':q.GetNumber()})
        for g in f.GraphicalItems():
            if g.GetLayer() in (p.F_Paste,p.B_Paste):record('paste_graphic',bounds(g),DIAMETER/2+PAD_PASTE_CLEARANCE,label=f.GetReference())
    # Keep the complete EP envelopes hole-free, including gaps between the nine
    # C5 EP islands where a smaller via might otherwise fit between paste pads.
    for ref,number in {'U101':'81','U1':'29','U201':'29','U301':'29','U401':'29'}.items():
        ep=[q for f in footprints if f.GetReference()==ref for q in f.Pads() if q.GetNumber()==number]
        if ep:
            boxes=[bounds(q) for q in ep]
            box=(min(r[0] for r in boxes),min(r[1] for r in boxes),max(r[2] for r in boxes),max(r[3] for r in boxes))
            record('ep_envelope',box,DIAMETER/2+PAD_PASTE_CLEARANCE,label=ref)
    for g in board.GetDrawings():
        if g.GetLayer() in (p.F_Paste,p.B_Paste):record('paste_graphic',bounds(g),DIAMETER/2+PAD_PASTE_CLEARANCE,label='board')
    signal_vias=[];excluded=collections.Counter()
    for t in list(board.GetTracks()):
        if isinstance(t,p.PCB_VIA):
            center=xy(t.GetPosition());drill=p.ToMM(t.GetDrill())
            hole_record(center,center,center,drill/2,t.m_Uuid.AsString())
            if t.GetNetname()=='GND':
                if t.GetViaType()==p.VIATYPE_THROUGH:
                    grounds.append({'xy':center,'type':'ground_through_via','uuid':t.m_Uuid.AsString()})
            else:
                radius=max(p.ToMM(t.GetWidth(layer))/2 for layer in layers if t.IsOnLayer(layer))
                record('via_copper',(center[0]-radius,center[1]-radius,center[0]+radius,center[1]+radius),
                       DIAMETER/2+COPPER_CLEARANCE,center=center,radius=radius,label=t.GetNetname())
            short=t.GetNetname().rsplit('/',1)[-1]
            if t.GetViaType()==p.VIATYPE_THROUGH and short not in POWER_NETS and t.GetNetCode():
                signal_vias.append(t)
            else:excluded[short]+=1
        elif t.GetNetname()!='GND':
            if isinstance(t,p.PCB_ARC):
                poly=p.SHAPE_POLY_SET()
                t.TransformShapeToPolygon(poly,t.GetLayer(),0,mm(.001),p.ERROR_OUTSIDE)
                record('arc_copper',bounds(t),DIAMETER/2+COPPER_CLEARANCE,poly=poly,label=t.GetNetname())
            else:
                record('track_copper',bounds(t),DIAMETER/2+COPPER_CLEARANCE,
                       a=xy(t.GetStart()),z=xy(t.GetEnd()),radius=p.ToMM(t.GetWidth())/2,label=t.GetNetname())
    ground_regions={layer:[] for layer in (p.In1_Cu,p.In2_Cu)}
    for z in board.Zones():
        if z.GetIsRuleArea() or z.GetNetname()!='GND':
            # Use the declared polygon, not just current fill: future refilling
            # must not put a new via into an intended non-ground copper region.
            record('rule_area' if z.GetIsRuleArea() else 'other_net_zone',bounds(z),DIAMETER/2+COPPER_CLEARANCE,
                   poly=z.Outline(),label=z.GetZoneName() or z.GetNetname())
        elif z.GetNetname()=='GND':
            for layer in ground_regions:
                if z.IsOnLayer(layer):ground_regions[layer].append(z.Outline())
    if any(not regions for regions in ground_regions.values()):
        raise ValueError('Expected intended GND planes on both inner layers')
    mounts=[xy(f.GetPosition()) for f in footprints if f.GetReference() in ('H1','H2','H3','H4')]
    edge=board.GetBoardEdgesBoundingBox()
    # A1 is a 100x100 mm rectangle. Reject another outline instead of treating
    # a bounding-box-only check as a general arbitrary-outline edge checker.
    extents=(p.ToMM(edge.GetLeft()),p.ToMM(edge.GetTop()),p.ToMM(edge.GetRight()),p.ToMM(edge.GetBottom()))
    if any(abs(a-z)>.1 for a,z in zip(extents,(0,0,100,100))):
        raise ValueError('Ground stitching assumes the reviewed 100x100 mm A1 outline')
    reject_totals=collections.Counter()
    def free(point, diameter=DIAMETER, drill=DRILL):
        # >=0.35 mm annulus-to-rectangular-edge allowance (board rule is .3).
        if not(.35+diameter/2<=point[0]<=99.65-diameter/2 and .35+diameter/2<=point[1]<=99.65-diameter/2):return 'board_edge'
        if any(math.dist(point,center)<3.5+diameter/2+PAD_PASTE_CLEARANCE for center in mounts):return 'M3_head_space'
        if any(not any(poly.Contains(V(point)) for poly in regions) for regions in ground_regions.values()):return 'outside_inner_ground_zone'
        for index in bins[(math.floor(point[0]/cell),math.floor(point[1]/cell))]:
            r=records[index]
            margin=r['margin']-((DRILL-drill)/2 if r['kind']=='hole' else (DIAMETER-diameter)/2)
            if rectdist(point,r['box'])>=margin+.000002:continue
            kind=r['kind']
            if kind in ('pad_or_paste','paste_graphic','ep_envelope'):return kind
            if kind=='hole':
                if segdist(point,r['a'],r['z'])<r['radius']+drill/2+HOLE_EDGE_CLEARANCE+.000002:return kind
            elif kind=='via_copper':
                if math.dist(point,r['center'])<r['radius']+diameter/2+COPPER_CLEARANCE+.000002:return kind
            elif kind=='track_copper':
                if segdist(point,r['a'],r['z'])<r['radius']+diameter/2+COPPER_CLEARANCE+.000002:return kind
            elif r['poly'].Collide(V(point),mm(diameter/2+COPPER_CLEARANCE+.000002)):
                return kind
        return None
    def neighbor(point):
        if not grounds:return None,None
        item=min(grounds,key=lambda g:math.dist(point,g['xy']))
        return item,math.dist(point,item['xy'])
    def describe_ground(item):
        if item is None:return None
        return {**{k:v for k,v in item.items() if k!='xy'},'position_mm':list(item['xy'])}
    rows=[];added=[];unserved=[]
    # Stable coordinate ordering makes additions reproducible for a fixed board.
    for source in sorted(signal_vias,key=lambda t:(t.GetNetname(),xy(t.GetPosition()))):
        center=xy(source.GetPosition());existing,distance=neighbor(center)
        row={'signal_via_uuid':source.m_Uuid.AsString(),'signal_net':source.GetNetname(),
             'signal_position_mm':list(center),'nearest_ground_before_mm':round(distance,6) if distance is not None else None}
        if distance is not None and distance<=NEIGHBOR_DISTANCE+.000002:
            row.update(status='existing_nearby_ground',nearest_ground=describe_ground(existing),distance_mm=round(distance,6))
            rows.append(row);continue
        angle0=math.atan2(existing['xy'][1]-center[1],existing['xy'][0]-center[0]) if existing else 0
        found=None;rejections=collections.Counter();tried=0
        # Ring radii 0.8..2.0 mm; 64 directions, starting toward nearest ground.
        offsets=[0]+[sign*k for k in range(1,32) for sign in (1,-1)]+[32]
        sizes=[(DIAMETER,DRILL)]+([(.45,.2)] if allow_small_fallback else [])
        selected_size=(DIAMETER,DRILL)
        for diameter,drill in sizes:
            for ring in range(8,21):
                radius=ring/10
                for k in offsets:
                    angle=angle0+k*math.pi/32
                    point=(round(center[0]+radius*math.cos(angle),4),round(center[1]+radius*math.sin(angle),4))
                    if math.dist(center,point)>NEIGHBOR_DISTANCE+.000002:continue
                    tried+=1;reason=free(point,diameter,drill)
                    if reason:rejections[reason]+=1;reject_totals[reason]+=1
                    else:found=point;selected_size=(diameter,drill);break
                if found is not None:break
            if found is not None:break
        if found is None:
            row.update(status='requires_manual_review',nearest_ground=describe_ground(existing),
                       distance_mm=round(distance,6) if distance is not None else None,
                       candidates_checked=tried,rejection_counts=dict(rejections))
            unserved.append(row);rows.append(row);continue
        diameter,drill=selected_size
        via=p.PCB_VIA(board);via.SetPosition(V(found));via.SetWidth(mm(diameter));via.SetDrill(mm(drill))
        via.SetViaType(p.VIATYPE_THROUGH);via.SetLayerPair(p.F_Cu,p.B_Cu);via.SetNet(ground_net)
        via.SetFrontTentingMode(p.TENTING_MODE_TENTED);via.SetBackTentingMode(p.TENTING_MODE_TENTED)
        board.Add(via)
        new={'xy':found,'type':'added_ground_through_via','uuid':via.m_Uuid.AsString(),'diameter_drill_mm':[diameter,drill]}
        grounds.append(new);hole_record(found,found,found,drill/2,via.m_Uuid.AsString())
        row.update(status='added_nearby_ground',nearest_ground=describe_ground(new),
                   distance_mm=round(math.dist(center,found),6),candidates_checked=tried)
        added.append(describe_ground(new));rows.append(row)
    # Additions for later transitions may also help earlier unserved transitions.
    remaining=[]
    for row in unserved:
        closest,distance=neighbor(tuple(row['signal_position_mm']))
        row['nearest_ground_after_mm']=round(distance,6) if distance is not None else None
        if distance is not None and distance<=NEIGHBOR_DISTANCE+.000002:
            row.update(status='served_by_later_added_ground',nearest_ground=describe_ground(closest),distance_mm=round(distance,6))
        else:remaining.append(row)
    return {
        'status':'requires_manual_review' if remaining else 'geometry_candidates_added_requires_DRC',
        'signal_through_vias_checked':len(signal_vias),'ground_vias_added':len(added),
        'excluded_supply_or_non_signal_vias_by_short_net':dict(sorted(excluded.items())),
        'criteria':{'nearby_ground_center_distance_mm':NEIGHBOR_DISTANCE,'new_via_diameter_drill_mm':[DIAMETER,DRILL],
                    'all_pad_paste_annulus_clearance_mm':PAD_PASTE_CLEARANCE,'other_net_copper_clearance_mm':COPPER_CLEARANCE,
                    'hole_edge_clearance_mm':HOLE_EDGE_CLEARANCE,'M3_head_radius_mm':3.5,
                    'candidate_ring_radius_mm':[.8,2.0],'small_fallback_diameter_drill_mm':[.45,.2] if allow_small_fallback else None,'ordinary_tenting':'both sides; not filled/capped'},
        'added_ground_vias':added,'unserved_signal_vias':remaining,'transitions':rows,
        'candidate_rejection_counts':dict(reject_totals),
        'limits':['No existing copper changed. The caller must refill and achieve KiCad DRC=0 before acceptance.',
                  'Plated-neighbor proximity does not prove ground connectivity, high-frequency loop inductance, impedance or timing.',
                  'Bounding boxes conservatively reject pad/custom-pad/paste areas. Signal classification excludes explicit supply/switch nets.',
                  'The intended continuous In1/In2 ground zones are checked by their outlines; final filled-plane integrity and connectivity must be verified separately.']}
