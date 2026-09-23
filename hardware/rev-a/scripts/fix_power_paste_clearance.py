"""Move three A1 tented vias clear of adjacent paste or mask apertures.

patch(board) changes only the specified via centres and incident same-net track
endpoints, retaining REG_RUN's existing B.Cu diagonal via one short added stub.
It neither loads nor saves a board. Matching power_placement.py source
coordinates are updated. Refill zones and run full DRC after applying the patch.
"""
import pcbnew as p


def patch(board):
    fixes=[('GND',(88.,30.6),(88.,30.85),.3),
           ('REG_RUN',(88.3,35.5),(88.3,35.75),.2),
           ('GND',(98.,26.54),(98.25,26.54),.3)]
    v=lambda xy:p.VECTOR2I(p.FromMM(xy[0]),p.FromMM(xy[1]))
    same=lambda a,b:abs(a.x-b.x)<=5 and abs(a.y-b.y)<=5
    report=[]
    for short,old,new,drill in fixes:
        candidates=[t for t in board.GetTracks() if isinstance(t,p.PCB_VIA)
                    and t.GetNetname().rsplit('/',1)[-1]==short
                    and (same(t.GetPosition(),v(old)) or same(t.GetPosition(),v(new)))]
        if len(candidates)!=1:
            raise RuntimeError(f'Expected one {short} via at {old} or {new}, found {len(candidates)}')
        via=candidates[0]
        if abs(via.GetDrillValue()-p.FromMM(drill))>1:
            raise RuntimeError(f'Unexpected drill for {short} via')
        was_applied=same(via.GetPosition(),v(new))
        endpoints=0
        stub_exists=False
        for t in board.GetTracks():
            if isinstance(t,p.PCB_VIA) or t.GetNetname()!=via.GetNetname():continue
            if short=='REG_RUN' and t.GetLayer()==p.B_Cu:
                if ((same(t.GetStart(),v(old)) and same(t.GetEnd(),v(new))) or
                    (same(t.GetEnd(),v(old)) and same(t.GetStart(),v(new)))):
                    stub_exists=True;continue
                # Also normalize a previously tested direct-move patch: keep
                # the long diagonal clear of the C11 GND via at (86.65,34.2).
                if same(t.GetStart(),v(new)):t.SetStart(v(old));endpoints+=1
                if same(t.GetEnd(),v(new)):t.SetEnd(v(old));endpoints+=1
                continue
            if same(t.GetStart(),v(old)):t.SetStart(v(new));endpoints+=1
            if same(t.GetEnd(),v(old)):t.SetEnd(v(new));endpoints+=1
        added=0
        if short=='REG_RUN' and not stub_exists:
            t=p.PCB_TRACK(board);t.SetStart(v(old));t.SetEnd(v(new));t.SetWidth(p.FromMM(.2));t.SetLayer(p.B_Cu);t.SetNet(via.GetNet());board.Add(t);added=1
        if not was_applied and endpoints==0:raise RuntimeError(f'Expected incident tracks for {short} via')
        via.SetPosition(v(new))
        report.append({'net':short,'old_mm':old,'new_mm':new,'moved_track_endpoints':endpoints,'added_short_B_Cu_stub':added,'already_applied':was_applied and endpoints==0 and added==0})
    board.BuildConnectivity()
    return report
