"""Fixed USB Full-Speed escape and coupled trunk; validate after every placement change."""
def route(board, footprints, nets=None):
    import pcbnew as p
    v=lambda xy:p.VECTOR2I(p.FromMM(xy[0]),p.FromMM(xy[1]))
    def pad(ref,num):return next(q for q in footprints[ref].Pads() if q.GetNumber()==str(num))
    def xy(ref,num):
        q=pad(ref,num).GetPosition();return (p.ToMM(q.x),p.ToMM(q.y))
    def trace(ref,num,points,layer=p.F_Cu,width=.158):
        net=pad(ref,num).GetNet()
        for a,b in zip(points,points[1:]):
            t=p.PCB_TRACK(board);t.SetStart(v(a));t.SetEnd(v(b));t.SetWidth(p.FromMM(width));t.SetLayer(layer);t.SetNet(net);board.Add(t)
    def via(ref,num,xy):
        t=p.PCB_VIA(board);t.SetPosition(v(xy));t.SetWidth(p.FromMM(.45));t.SetDrill(p.FromMM(.2));t.SetViaType(p.VIATYPE_THROUGH);t.SetLayerPair(p.F_Cu,p.B_Cu);t.SetNet(pad(ref,num).GetNet());board.Add(t)
    # A pins carry the main differential path; the reversed Type-C row is joined
    # with short bottom escapes. Both copper layers have a continuous ground reference.
    trace('J102','A6',[xy('J102','A6'),(50.25,8.9),(50.95,9.6),xy('D101',1)])
    trace('J102','A7',[xy('J102','A7'),(49.75,8.75),(49.05,9.45),xy('D101',3)])
    trace('J102','B6',[xy('J102','B6'),(49.25,8.6)])
    trace('J102','B6',[(49.25,8.6),(49.55,8.9),(50.25,8.9)],p.B_Cu)
    via('J102','B6',(49.25,8.6));via('J102','A6',(50.25,8.9))
    trace('J102','B7',[xy('J102','B7'),(50.75,8.3),(51.35,8.9)])
    trace('J102','B7',[(51.35,8.9),(51.35,9.9),(49.05,9.9)],p.B_Cu)
    via('J102','B7',(51.35,8.9));via('J102','A7',(49.05,9.9))
    # ESD is at the connector; leave its rail and ground connections to the local
    # power routing. Common ports need an escape around the USB switch package.
    trace('D101',6,[xy('D101',6),(50.95,14.2),(53.3,16.55),(53.3,18.5),xy('U103',4)])
    trace('D101',4,[xy('D101',4),(49.05,14.2),(46.7,16.55),(46.7,18.0),xy('U103',6)])
    # Swap package port ordering using a short B.Cu crossover, then a straight
    # nominal 90-ohm trunk (W=.158, gap=.200 mm, JLC04161H-3313).
    trace('U103',2,[xy('U103',2),(53.15,19.5),(53.15,21.25),(52.8,21.6)])
    via('U103',2,(52.8,21.6));via('U103',2,(48.65,24.6))
    trace('U103',2,[(52.8,21.6),(52.8,22.5),(49,22.5),(48.65,24.6)],p.B_Cu)
    trace('U103',2,[(48.65,24.6),(50,25.95),(50,40.69),xy('R110',1)])
    trace('U103',8,[xy('U103',8),(46.5,19),(46.5,21.5),(50.358,25.358),(50.358,40.048),xy('R111',1)])
    for xyv in [(48.0,9.7),(52.2,10),(53.7,21.6),(47.8,24.6)]:via('D101',2,xyv)
