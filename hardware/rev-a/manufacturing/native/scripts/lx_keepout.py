"""Only change the existing RP LX L2 rule-area outline in an in-memory board.
Caller must refill, DRC and save the routed board; this module never loads/saves.
"""
OLD=[(52.2,39.9),(54.3,39.9),(54.3,42.4),(53.6,43.2),(52.2,43.2)]
NEW=[(52.2,39.9),(54.3,39.9),(54.3,42.4),(53.6,43.2),(53.3,43.2),(53.3,45.65),(52.7,45.65),(52.7,43.2),(52.2,43.2)]
NAME='RP_LX_L2_COPPER_KEEPOUT'
def patch(board):
    import pcbnew as p
    def points(z):
        poly=z.Outline()
        if poly.OutlineCount()!=1:return []
        o=poly.Outline(0)
        return [(round(p.ToMM(o.CPoint(i).x),6),round(p.ToMM(o.CPoint(i).y),6)) for i in range(o.PointCount())]
    matches=[z for z in board.Zones() if z.GetIsRuleArea() and z.IsOnLayer(p.In1_Cu) and (points(z)==OLD or (z.GetZoneName()==NAME and points(z)==NEW))]
    if len(matches)!=1:raise RuntimeError('Expected exactly one unchanged original/already-patched RP LX rule area; found '+str(len(matches)))
    z=matches[0]
    if points(z)==NEW:return {'changed':False,'outline_mm':NEW}
    outline=z.Outline();outline.RemoveAllContours();outline.NewOutline()
    for x,y in NEW:outline.Append(p.FromMM(x),p.FromMM(y))
    z.SetZoneName(NAME)
    return {'changed':True,'old_outline_mm':OLD,'outline_mm':NEW,'requires':'Refill existing copper zones, rerun full DRC/connectivity; do not rebuild or discard routed tracks.'}
