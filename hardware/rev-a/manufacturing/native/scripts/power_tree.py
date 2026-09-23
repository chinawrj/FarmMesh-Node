#!/usr/bin/env python3
"""Route B.Cu power distribution between reviewed local power-domain anchors.

Uses a conservative board-copper obstacle map and shortest-path search. Local
high-current converter loops are supplied by power_placement.py, not this file.
DRC remains the acceptance test. Run with KiCad Python (which calls the small
stdlib-only path solver via the normal Python runtime).
"""
import heapq, math

def route(board, footprints, nets=None, source=(68.0,28.7), rp_feed=None):
    import pcbnew as p
    net=next(q.GetNet() for q in footprints['C7'].Pads() if q.GetNumber()=='1')
    toxy=lambda q:(p.ToMM(q.x),p.ToMM(q.y))
    targets=[('A',(4.85,33.4),1.5),('B',(33.4,95.15),1.5),('C',(95.15,67.4),1.5)]
    if rp_feed:targets.append(('RP',tuple(rp_feed),1.0))
    def bbox(bx):return (*toxy(bx.GetOrigin()),*toxy(bx.GetEnd()))
    rectangles=[];circles=[];segments=[]
    for f in board.GetFootprints():
        for pad in f.Pads():
            if pad.GetNetCode()==net.GetNetCode():continue
            if not pad.IsOnLayer(p.B_Cu) and not pad.GetDrillSize().x:continue
            rectangles.append(bbox(pad.GetBoundingBox()))
    for t in board.GetTracks():
        if t.GetNetCode()==net.GetNetCode():continue
        if isinstance(t,p.PCB_VIA):circles.append((*toxy(t.GetPosition()),p.ToMM(t.GetWidth(p.B_Cu))/2))
        elif t.IsOnLayer(p.B_Cu):segments.append((toxy(t.GetStart()),toxy(t.GetEnd()),p.ToMM(t.GetWidth())/2))
    for z in board.Zones():
        if z.IsOnLayer(p.B_Cu) and not z.GetIsRuleArea() and z.GetNetCode()!=net.GetNetCode():rectangles.append(bbox(z.GetBoundingBox()))
    # Reserve the RP local core/crystal/flash region; long power trunks stay outside.
    rectangles.append((40,36,60,66))
    out={}
    for label,target,width in targets:
        margin=width/2+.17;step=.25;maxidx=400
        if label=='RP':obsrects=rectangles[:-1]
        else:obsrects=rectangles
        def dist_seg(x,y,a,b):
            ax,ay=a;bx,by=b;dx=bx-ax;dy=by-ay
            tt=max(0,min(1,((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy))) if dx*dx+dy*dy else 0
            return math.hypot(x-ax-tt*dx,y-ay-tt*dy)
        cache={}
        def free(ij):
            if ij in cache:return cache[ij]
            x,y=ij[0]*step,ij[1]*step
            ok=margin+.3<=x<=100-margin-.3 and margin+.3<=y<=100-margin-.3
            if ok:
                for x0,y0,x1,y1 in obsrects:
                    if x0-margin<=x<=x1+margin and y0-margin<=y<=y1+margin:ok=False;break
            if ok:
                for xx,yy,r in circles:
                    if (x-xx)**2+(y-yy)**2<(r+margin)**2:ok=False;break
            if ok:
                for aa,bb,rr in segments:
                    if dist_seg(x,y,aa,bb)<rr+margin:ok=False;break
            cache[ij]=ok;return ok
        start=tuple(round(z/step) for z in source);end=tuple(round(z/step) for z in target)
        # Exact anchors are connected to their nearest quarter-mm nodes below.
        if not free(start) or not free(end):
            raise RuntimeError(f'{label} power anchor obstructed for {width}mm: {source}, {target}')
        goal=lambda a:math.hypot(a[0]-end[0],a[1]-end[1])
        queue=[(goal(start),0,start)];score={start:0};previous={};done=False
        while queue:
            _,cost,cur=heapq.heappop(queue)
            if cost>score[cur]+1e-8:continue
            if cur==end:done=True;break
            for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
                nx=(cur[0]+dx,cur[1]+dy)
                if not free(nx):continue
                if dx and dy and (not free((cur[0]+dx,cur[1])) or not free((cur[0],cur[1]+dy))):continue
                nc=cost+math.hypot(dx,dy)
                if nc<score.get(nx,1e30):score[nx]=nc;previous[nx]=cur;heapq.heappush(queue,(nc+goal(nx),nc,nx))
        if not done:raise RuntimeError('No power path '+label)
        seq=[end]
        while seq[-1]!=start:seq.append(previous[seq[-1]])
        seq.reverse();simple=[seq[0]]
        for i in range(1,len(seq)-1):
            d1=(seq[i][0]-seq[i-1][0],seq[i][1]-seq[i-1][1]);d2=(seq[i+1][0]-seq[i][0],seq[i+1][1]-seq[i][1])
            if d1!=d2:simple.append(seq[i])
        simple.append(seq[-1]);points=[source]+[(a*step,b*step) for a,b in simple]+[target]
        length=0
        for a,b in zip(points,points[1:]):
            if a==b:continue
            t=p.PCB_TRACK(board);t.SetStart(p.VECTOR2I(p.FromMM(a[0]),p.FromMM(a[1])));t.SetEnd(p.VECTOR2I(p.FromMM(b[0]),p.FromMM(b[1])));t.SetWidth(p.FromMM(width));t.SetLayer(p.B_Cu);t.SetNet(net);board.Add(t);length+=math.dist(a,b)
        out[label]={'width_mm':width,'length_mm':round(length,3),'path_mm':points,'estimated_20C_resistance_mOhm':round(17.2*length/(width*35),2)}
    return out
