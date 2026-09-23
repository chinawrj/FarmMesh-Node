"""Short ground access for otherwise isolated A1 discrete/USB pads.

Call route(board, footprints, nets) after the local routes. The caller supplies
continuous inner GND planes and performs final fill/DRC. No board is loaded or
saved. Existing local ground tracks and through-hole ground access are retained.
All new vias are ordinary tented 0.6/0.3mm vias, outside every pad/paste opening.
"""
import math

REFERENCES = (
    'J102','U103','U104','D101','C126','C127','C128','C129','C130',
    'R108','R109','R113','R115','R104','SW101','SW102',
    'R204','R304','R404','TP3','TP102',
    'SW201','SW202','SW301','SW302','SW401','SW402',
)


def route(board, footprints, nets=None):
    import pcbnew as p
    mm=p.FromMM
    xy=lambda q:(p.ToMM(q.x),p.ToMM(q.y))
    V=lambda q:p.VECTOR2I(mm(q[0]),mm(q[1]))
    width=.25;diam=.6;drill=.3;clearance=.17
    count={'segments':0,'vias':0,'pads_connected':0,'already_connected':[],
           'remaining':[],'access':[]}
    board.BuildConnectivity()
    connectivity=board.GetConnectivity()
    pads=[q for f in board.GetFootprints() for q in f.Pads()]
    obstacles=[]
    def bbox(q):
        r=q.GetBoundingBox();return (*xy(r.GetOrigin()),*xy(r.GetEnd()))
    def inflate(r,d):return (r[0]-d,r[1]-d,r[2]+d,r[3]+d)
    def pointrect(q,r):return r[0]<=q[0]<=r[2] and r[1]<=q[1]<=r[3]
    def segrect(a,b,r):
        # Liang-Barsky segment/closed-rectangle intersection.
        lo,hi=0.,1.;dx=b[0]-a[0];dy=b[1]-a[1]
        for pp,qq in [(-dx,a[0]-r[0]),(dx,r[2]-a[0]),(-dy,a[1]-r[1]),(dy,r[3]-a[1])]:
            if abs(pp)<1e-12:
                if qq<0:return False
            elif pp<0:lo=max(lo,qq/pp)
            else:hi=min(hi,qq/pp)
            if lo>hi:return False
        return True
    def pointseg(q,a,b):
        d=(b[0]-a[0],b[1]-a[1]);den=d[0]*d[0]+d[1]*d[1]
        t=max(0,min(1,((q[0]-a[0])*d[0]+(q[1]-a[1])*d[1])/den)) if den else 0
        return math.hypot(q[0]-a[0]-t*d[0],q[1]-a[1]-t*d[1])
    def segdist(a,b,c,d):
        def cross(v,w):return v[0]*w[1]-v[1]*w[0]
        ab=(b[0]-a[0],b[1]-a[1]);cd=(d[0]-c[0],d[1]-c[1]);ca=(c[0]-a[0],c[1]-a[1])
        den=cross(ab,cd)
        if abs(den)>1e-12:
            t=cross(ca,cd)/den;u=cross(ca,ab)/den
            if 0<=t<=1 and 0<=u<=1:return 0.
        return min(pointseg(a,c,d),pointseg(b,c,d),pointseg(c,a,b),pointseg(d,a,b))

    # Bounding boxes deliberately overestimate rounded/rotated pads. New vias
    # remain wholly outside pad copper (+0.05mm), not merely outside the drill.
    pad_boxes=[(q,bbox(q)) for q in pads]
    for q,r in pad_boxes:
        if q.GetNetname()!='GND':obstacles.append(('pad',q,r))
    def copper_clear(a,b,via_point=None):
        for kind,q,r in obstacles:
            if q.IsOnLayer(p.F_Cu) and segrect(a,b,inflate(r,width/2+clearance)):
                return False
            if via_point and pointrect(via_point,inflate(r,diam/2+clearance)):
                return False
        if via_point:
            if not(.8<=via_point[0]<=99.2 and .8<=via_point[1]<=99.2):return False
            for q,r in pad_boxes:
                if pointrect(via_point,inflate(r,diam/2+.05)):return False
            # Conservatively avoid rule areas and other-net copper zones.
            for z in board.Zones():
                if z.GetIsRuleArea() or z.GetNetname()!='GND':
                    if pointrect(via_point,inflate(bbox(z),diam/2+clearance)):
                        return False
        for t in board.GetTracks():
            if t.GetNetname()=='GND':
                if via_point and isinstance(t,p.PCB_VIA):
                    # Distinct holes need >=0.20mm edge spacing.
                    if math.dist(via_point,xy(t.GetPosition())) < (drill+p.ToMM(t.GetDrill()))/2+.21:
                        return False
                continue
            if isinstance(t,p.PCB_VIA):
                r=p.ToMM(t.GetWidth(p.F_Cu))/2
                if pointseg(xy(t.GetPosition()),a,b)<r+width/2+clearance:return False
                if via_point and math.dist(via_point,xy(t.GetPosition()))<r+diam/2+clearance:return False
            else:
                aa,bb=xy(t.GetStart()),xy(t.GetEnd());r=p.ToMM(t.GetWidth())/2
                if t.IsOnLayer(p.F_Cu) and segdist(a,b,aa,bb)<r+width/2+clearance:return False
                if via_point and pointseg(via_point,aa,bb)<r+diam/2+clearance:return False
        return True

    seen=set()
    for ref in REFERENCES:
        f=footprints.get(ref)
        if f is None:continue
        for pad in f.Pads():
            if pad.GetNetname()!='GND':continue
            start=xy(pad.GetPosition());key=tuple(round(a,5)for a in start)
            label=f'{ref}.{pad.GetNumber()}@{start[0]:.4f},{start[1]:.4f}'
            # Repeated physical same-number pads need separate accesses, but
            # stacked USB A/B contacts at identical coordinates share one.
            if key in seen:continue
            seen.add(key)
            if pad.GetDrillSize().x or len(connectivity.GetConnectedTracks(pad)):
                count['already_connected'].append(label);continue
            existing=[]
            for t in board.GetTracks():
                if isinstance(t,p.PCB_VIA) and t.GetNetname()=='GND':
                    at=xy(t.GetPosition())
                    if math.dist(start,at)<=1.8:existing.append(at)
            for q in pads:
                if q.GetNetname()=='GND' and q.GetDrillSize().x:
                    at=xy(q.GetPosition())
                    if math.dist(start,at)<=2.0:existing.append(at)
            found=None;new_via=True
            for at in sorted(existing,key=lambda a:math.dist(start,a)):
                if copper_clear(start,at):found=at;new_via=False;break
            if found is None:
                fc=xy(f.GetPosition());prefer=math.atan2(start[1]-fc[1],start[0]-fc[0])
                candidates=[]
                for distance in [.8,.9,1.0,1.1,1.2,1.3,1.5,1.8,2.2,2.6,3.0]:
                    for k in range(32):
                        angle=prefer+k*math.pi/16
                        at=(round(start[0]+distance*math.cos(angle),4),round(start[1]+distance*math.sin(angle),4))
                        turn=abs(math.atan2(math.sin(angle-prefer),math.cos(angle-prefer)))
                        candidates.append((distance+turn*.08,at))
                for _,at in sorted(candidates):
                    if copper_clear(start,at,at):found=at;break
            if found is None:
                count['remaining'].append(label);continue
            if new_via:
                v=p.PCB_VIA(board);v.SetPosition(V(found));v.SetWidth(mm(diam));v.SetDrill(mm(drill))
                v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(pad.GetNet())
                v.SetFrontTentingMode(p.TENTING_MODE_TENTED);v.SetBackTentingMode(p.TENTING_MODE_TENTED)
                board.Add(v);count['vias']+=1
            t=p.PCB_TRACK(board);t.SetStart(V(start));t.SetEnd(V(found));t.SetWidth(mm(width));t.SetLayer(p.F_Cu);t.SetNet(pad.GetNet());board.Add(t)
            count['segments']+=1;count['pads_connected']+=1
            count['access'].append({'pad':label,'via_or_existing_ground_mm':list(found),'new_via':new_via})
    return count
