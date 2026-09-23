"""Add A1 ground-plane access and the three remaining low-current 3V3 tails.

route(board) adds copper only. It does not load/save a board, move footprints,
remove tracks, or fill zones. Call on a filled original SES + restored seed;
refill and perform full DRC afterward. Ordinary tented vias stay outside pads.
"""
import heapq
import math
import pcbnew as p


def xy(v):
    return p.ToMM(v.x), p.ToMM(v.y)


def vec(q):
    return p.VECTOR2I(p.FromMM(q[0]), p.FromMM(q[1]))


def box(item):
    r = item.GetBoundingBox()
    return (*xy(r.GetOrigin()), *xy(r.GetEnd()))


def inflated(r, d):
    return r[0]-d, r[1]-d, r[2]+d, r[3]+d


def inrect(q, r):
    return r[0] <= q[0] <= r[2] and r[1] <= q[1] <= r[3]


def segrect(a, b, r):
    lo, hi = 0., 1.
    dx, dy = b[0]-a[0], b[1]-a[1]
    for pp, qq in [(-dx,a[0]-r[0]), (dx,r[2]-a[0]), (-dy,a[1]-r[1]), (dy,r[3]-a[1])]:
        if abs(pp) < 1e-12:
            if qq < 0: return False
        elif pp < 0: lo = max(lo, qq/pp)
        else: hi = min(hi, qq/pp)
        if lo > hi: return False
    return True


def pointseg(q, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    den = dx*dx+dy*dy
    t = max(0, min(1, ((q[0]-a[0])*dx+(q[1]-a[1])*dy)/den)) if den else 0
    return math.hypot(q[0]-a[0]-t*dx, q[1]-a[1]-t*dy)


def segdist(a, b, c, d):
    def cross(v,w): return v[0]*w[1]-v[1]*w[0]
    ab,cd,ca=(b[0]-a[0],b[1]-a[1]),(d[0]-c[0],d[1]-c[1]),(c[0]-a[0],c[1]-a[1])
    den=cross(ab,cd)
    if abs(den)>1e-12 and 0<=cross(ca,cd)/den<=1 and 0<=cross(ca,ab)/den<=1: return 0.
    return min(pointseg(a,c,d),pointseg(b,c,d),pointseg(c,a,b),pointseg(d,a,b))


class Clearance:
    def __init__(self, board, net, width, layer):
        self.b,self.net,self.width,self.layer=board,net,width,layer
        self.pads=[q for f in board.GetFootprints() for q in f.Pads()]
        self.padboxes=[(q,box(q)) for q in self.pads]
        self.tracks=list(board.GetTracks())

    def clear(self,a,b,via=False):
        gap=.17
        for pad,r in self.padboxes:
            if pad.GetNetname()!=self.net:
                if pad.IsOnLayer(self.layer) and segrect(a,b,inflated(r,self.width/2+gap)): return False
                if via and inrect(b,inflated(r,.3+gap)): return False
            # No via annulus inside a pad/paste opening, even on its own net.
            if via and inrect(b,inflated(r,.35)): return False
        for z in self.b.Zones():
            if z.GetIsRuleArea() or (z.GetNetname() not in (self.net,'GND') and z.IsOnLayer(self.layer)):
                if segrect(a,b,inflated(box(z),self.width/2+gap)): return False
        for t in self.tracks:
            if isinstance(t,p.PCB_VIA):
                at=xy(t.GetPosition());r=p.ToMM(t.GetWidth(p.F_Cu))/2
                if t.GetNetname()!=self.net:
                    if pointseg(at,a,b)<r+self.width/2+gap: return False
                    if via and math.dist(at,b)<r+.3+gap:return False
                elif via and math.dist(at,b)<(p.ToMM(t.GetDrillValue())+.3)/2+.21:return False
            elif t.GetNetname()!=self.net:
                aa,bb=xy(t.GetStart()),xy(t.GetEnd());r=p.ToMM(t.GetWidth())/2
                if t.IsOnLayer(self.layer) and segrect(a,b,inflated(box(t),self.width/2+gap)):
                    if segdist(a,b,aa,bb)<r+self.width/2+gap:return False
                if via and pointseg(b,aa,bb)<r+.3+gap:return False
        return True


def add_path(board, net, points, width, layer):
    keys={(t.GetNetname(),t.GetLayer(),p.ToMM(t.GetWidth()),tuple(sorted((xy(t.GetStart()),xy(t.GetEnd())))))
          for t in board.GetTracks() if not isinstance(t,p.PCB_VIA)}
    added=0
    for a,b in zip(points,points[1:]):
        if math.dist(a,b)<1e-7:continue
        key=(net.GetNetname(),layer,width,tuple(sorted((a,b))))
        if key in keys:continue
        t=p.PCB_TRACK(board);t.SetStart(vec(a));t.SetEnd(vec(b));t.SetWidth(p.FromMM(width));t.SetLayer(layer);t.SetNet(net);board.Add(t)
        keys.add(key);added+=1
    return added


def add_via(board,net,at):
    t=p.PCB_VIA(board);t.SetPosition(vec(at));t.SetWidth(p.FromMM(.6));t.SetDrill(p.FromMM(.3))
    t.SetViaType(p.VIATYPE_THROUGH);t.SetLayerPair(p.F_Cu,p.B_Cu);t.SetNet(net)
    t.SetFrontTentingMode(p.TENTING_MODE_TENTED);t.SetBackTentingMode(p.TENTING_MODE_TENTED);board.Add(t)


def grid_path(board,net,start,end,width=.3):
    check=Clearance(board,net,width,p.B_Cu)
    if check.clear(start,end):return [start,end]
    step=.25
    ss=(round(start[0]/step),round(start[1]/step));ee=(round(end[0]/step),round(end[1]/step))
    pos=lambda q:(q[0]*step,q[1]*step)
    if not check.clear(start,pos(ss)) or not check.clear(pos(ee),end):
        raise RuntimeError(f'Cannot reach route grid: {start} -> {end}')
    queue=[(math.dist(ss,ee),0.,ss)];cost={ss:0.};parent={};visited=set()
    while queue:
        _,g,u=heapq.heappop(queue)
        if u in visited:continue
        visited.add(u)
        if u==ee:break
        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
            v=(u[0]+dx,u[1]+dy)
            if not(35<=v[0]*step<=72 and 10<=v[1]*step<=40):continue
            ng=g+math.hypot(dx,dy)
            if ng>=cost.get(v,float('inf')) or not check.clear(pos(u),pos(v)):continue
            cost[v]=ng;parent[v]=u;heapq.heappush(queue,(ng+math.dist(v,ee),ng,v))
    if ee not in visited:raise RuntimeError(f'No clear B.Cu route: {start} -> {end}')
    path=[ee]
    while path[-1]!=ss:path.append(parent[path[-1]])
    path=[start]+[pos(q)for q in reversed(path)]+[end]
    # Greedy visibility simplification retains checked clearance for each leg.
    result=[path[0]];i=0
    while i<len(path)-1:
        j=len(path)-1
        while j>i+1 and not check.clear(path[i],path[j]):j-=1
        result.append(path[j]);i=j
    return result


def route(board):
    nets={n.GetNetname():n for n in board.GetNetsByNetcode().values()}
    report={'ground_access':[],'power_tails':[],'segments':0,'vias':0,'remaining':[]}
    board.BuildConnectivity();conn=board.GetConnectivity()
    allpads=[q for f in board.GetFootprints()for q in f.Pads()]
    seen=set();groups=[]
    for pad in allpads:
        if pad.GetNetname()!='GND' or pad.m_Uuid.AsString() in seen:continue
        members=list(conn.GetConnectedItems(pad));seen.update(q.m_Uuid.AsString()for q in members)
        # A track alone is insufficient. Require a physically connected filled
        # inner GND zone; isolated router chains otherwise receive local access.
        if any(isinstance(q,p.ZONE) and not q.GetIsRuleArea() and q.GetNetname()=='GND' and
               (q.IsOnLayer(p.In1_Cu) or q.IsOnLayer(p.In2_Cu)) for q in members):continue
        groups.append([q for q in members if isinstance(q,p.PAD) and q.IsOnLayer(p.F_Cu)])
    for pads in groups:
        check=Clearance(board,'GND',.25,p.F_Cu);found=None
        for pad in sorted(pads,key=lambda q:(q.GetParentFootprint().GetReference(),q.GetNumber(),xy(q.GetPosition()))):
            start=xy(pad.GetPosition());fc=xy(pad.GetParentFootprint().GetPosition());pref=math.atan2(start[1]-fc[1],start[0]-fc[0])
            for radius in [.8,.9,1.,1.1,1.2,1.3,1.5,1.8,2.2,2.6,3.]:
                for k in range(32):
                    angle=pref+k*math.pi/16;at=(round(start[0]+radius*math.cos(angle),4),round(start[1]+radius*math.sin(angle),4))
                    if not check.clear(start,at,True):continue
                    if not any(z.GetNetname()=='GND' and not z.GetIsRuleArea() and z.IsOnLayer(p.In1_Cu) and
                               z.HitTestFilledArea(p.In1_Cu,vec(at))for z in board.Zones()):continue
                    found=(pad,start,at);break
                if found:break
            if found:break
        if not found:
            report['remaining'].append([q.GetParentFootprint().GetReference()+'.'+q.GetNumber()for q in pads]);continue
        pad,start,at=found;add_via(board,nets['GND'],at);report['vias']+=1
        report['segments']+=add_path(board,nets['GND'],[start,at],.25,p.F_Cu)
        report['ground_access'].append({'pad':pad.GetParentFootprint().GetReference()+'.'+pad.GetNumber(),'start_mm':start,'via_mm':at})
    # Original-session low-current USB/control and debug/reference branches.
    # All three destination points lie on the reviewed wide 3V3 distribution.
    for start,end in [((61.7679,34.5677),(61.,34.2)),((66.,27.1562),(68.,28.7)),((52.4742,14.2311),(68.,28.7))]:
        source=next((q for q in board.GetTracks()if isinstance(q,p.PCB_VIA) and q.GetNetname()=='+3V3' and math.dist(xy(q.GetPosition()),start)<1e-5),None)
        if source is None:raise RuntimeError(f'Expected original-session supply via missing: {start}')
        board.BuildConnectivity();members=board.GetConnectivity().GetConnectedItems(source)
        if any(not isinstance(q,p.PCB_VIA) and isinstance(q,p.PCB_TRACK) and q.GetLayer()==p.B_Cu and
               q.GetWidth()>=p.FromMM(.3) and pointseg(end,xy(q.GetStart()),xy(q.GetEnd()))<.01 for q in members):continue
        path=grid_path(board,'+3V3',start,end,.3)
        report['segments']+=add_path(board,nets['+3V3'],path,.3,p.B_Cu)
        report['power_tails'].append({'width_mm':.3,'layer':'B.Cu','path_mm':path})
    board.BuildConnectivity()
    return report
