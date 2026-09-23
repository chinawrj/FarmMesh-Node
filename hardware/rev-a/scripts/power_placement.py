"""LTC3119 FE placement and explicit critical copper for the A1 seed.

Import placements() before placing footprints, then call route(board, footprints,
nets). No board is loaded or saved here. Dimensions are millimetres. The caller
must supply continuous In1/In2 ground and run final full-board DRC/fill/review.
"""
import math
import pcbnew as pcb


def placements():
    return {
        'U1': (80, 27, 0), 'L1': (80, 17, 180),
        'C1': (85.5, 23.3, 0), 'C2': (74.5, 23.3, 180),
        'C3': (85.2, 27.5, -90), 'C4': (87.4, 27.5, -90),
        'C5': (88.7, 30.0, 180), 'C6': (94, 17, 90),
        'C7': (71.8, 17, 90), 'C8': (74.8, 27.5, -90),
        'C9': (71.8, 28.7, 0), 'C11': (85.7, 33.2, 0),
        'D1': (83.4, 37, 180),
        'R2': (73.6, 32.0, 0), 'R3': (75.4, 34.4, -90),
        'R4': (78.3, 34.4, -90), 'C10': (78.3, 37.5, -90),
        'R5': (85.7, 30.3, 0), 'R6': (70, 31, 0),
        'R7': (88.3, 34.2, -90), 'R8': (91.3, 34.2, -90),
        'C12': (92.8, 34.2, -90), 'J2': (97, 24, 0),
        'J1': (88, 40, 0), 'F1': (96.4, 34.5, 90),
        'Q1': (92.3, 29.7, 0), 'R1': (91, 26.2, -90),
    }


def requirements():
    """JSON-compatible review constraints for the caller's build report."""
    return {
        'source': 'https://www.analog.com/media/en/technical-documentation/data-sheets/3119fb.pdf',
        'reference': 'FE Figure 11, pp25-26; TA06 p28',
        'layers': {'F.Cu': 'local bypass/SW/quiet controls',
                   'In1.Cu': 'continuous GND', 'In2.Cu': 'continuous GND',
                   'B.Cu': 'wide battery and output distribution, local crossings'},
        'L1_orientation': '180 deg: pad1 SW1 right, pad2 SW2 left; do not rotate independently',
        'input_assumption': '2.2A output at Vin3.0V/80% requires about3.03A input; 3A pulse needs4.13A',
        'track_width_mm': {'trunks': 1.0, 'battery': 1.5,
                           'SW_under_ceramic_body': 0.6, 'IC_escape': 0.30},
        'capacitor_orientation': 'C3/C4/C8 bridge over the lower SW branch; do not move independently',
        'EP_vias': 'Nine 0.6/0.3mm peripheral GND vias outside exposed-pad mask/paste; three 0.8mm copper strips to EP; thermal validation required',
        'J1_courtyard': 'extends to y45.3mm; reserve connector area to y46mm',
        'pending': ['full-board courtyard/copper DRC', 'post-fill connectivity',
                    'thermal/current/loop measurements', 'final input MLCC DC-bias evidence'],
    }


def route(board, footprints, nets):
    """Add the power-cell routes once, after placements and pad nets are set.

    Uses pad positions from actual FootprintLoad results. Missing or moved parts
    cause failure instead of silently drawing stale routes. Net lookup accepts
    either hierarchical net names or short names, as used by build_pcb.py.
    """
    mm = pcb.FromMM
    vec = lambda x, y: pcb.VECTOR2I(mm(x), mm(y))
    by_short = {str(k).rsplit('/', 1)[-1]: n for k, n in nets.items()}
    counts = {'segments': 0, 'vias': 0, 'zones': 0}
    for ref, (x, y, angle) in placements().items():
        f = footprints[ref]
        xy = f.GetPosition()
        if math.hypot(pcb.ToMM(xy.x)-x, pcb.ToMM(xy.y)-y) > .001:
            raise ValueError('power placement moved: '+ref)
        if abs((f.GetOrientationDegrees()-angle+180) % 360-180) > .001:
            raise ValueError('power orientation moved: '+ref)

    def pos(ref, number):
        pads = [p for p in footprints[ref].Pads() if p.GetNumber() == str(number)]
        if len(pads) != 1:
            raise ValueError(f'Expected one copper pad {ref}.{number}')
        p = pads[0]
        v = p.GetPosition()
        return (pcb.ToMM(v.x), pcb.ToMM(v.y))

    def tr(net, points, width=.3, layer=pcb.F_Cu):
        for a, z in zip(points, points[1:]):
            if math.dist(a, z) < .0001:
                continue
            t = pcb.PCB_TRACK(board)
            t.SetStart(vec(*a)); t.SetEnd(vec(*z)); t.SetWidth(mm(width))
            t.SetLayer(layer); t.SetNet(by_short[net]); board.Add(t)
            counts['segments'] += 1

    def via(net, xy, diameter=.6, drill=.3):
        v = pcb.PCB_VIA(board); v.SetPosition(vec(*xy))
        v.SetWidth(mm(diameter)); v.SetDrill(mm(drill))
        v.SetViaType(pcb.VIATYPE_THROUGH)
        v.SetLayerPair(pcb.F_Cu, pcb.B_Cu); v.SetNet(by_short[net])
        board.Add(v); counts['vias'] += 1

    def gvia(ref, number, xy, width=.4):
        tr('GND', [pos(ref, number), xy], width)
        via('GND', xy)

    # SW trunks mirror the manufacturer's FE floorplan. Two power pins per
    # switch join outside the PVIN/PVOUT island. Lower branch crosses only the
    # ceramic body gap (0.6mm), never its supply/ground pads.
    tr('SW1', [pos('U1',24),(84.4,25.375),(85.1,25.375)], .3)
    tr('SW1', [(85.1,25.375),(89.3,25.375)], 1.0)
    tr('SW1', [pos('U1',21),(83.85,27.325),(84.4,27.5)], .3)
    tr('SW1', [(84.4,27.5),(89.3,27.5)], .6)
    tr('SW1', [(89.3,27.5),(89.3,20.7),(82.41,20.7),pos('L1',1)], 1.0)
    tr('SW1', [pos('C1',2),(89.3,23.3)], .3)
    tr('BST1', [pos('U1',26),(83.9,24.075),(84.725,23.3),pos('C1',1)], .2)

    tr('SW2', [pos('U1',5),(75.6,25.375),(74.9,25.375)], .3)
    tr('SW2', [(74.9,25.375),(73.35,25.375)], 1.0)
    tr('SW2', [pos('U1',8),(76.15,27.325),(75.6,27.5)], .3)
    tr('SW2', [(75.6,27.5),(73.35,27.5)], .6)
    tr('SW2', [(73.35,27.5),(73.35,20.7),(77.59,20.7),pos('L1',2)], 1.0)
    tr('SW2', [pos('C2',2),(73.35,23.3)], .3)
    tr('BST2', [pos('U1',3),(76.1,24.075),(75.275,23.3),pos('C2',1)], .2)

    # Local PVIN/PVOUT islands, dual vias per island. The bulk capacitor/main
    # distribution comes in on B.Cu; both adjacent inner planes remain GND.
    for net, pin_a, pin_b, vx, cap, cap_x in [
            ('VBAT_PROTECTED',23,22,84.15,'C3',85.2),
            ('+3V3',6,7,75.85,'C8',74.8)]:
        for pin, yy in [(pin_a,26.025),(pin_b,26.675)]:
            tr(net,[pos('U1',pin),(vx,yy)], .3)
            via(net,(vx,yy),.55,.3)
        tr(net,[(vx,26.025),(vx,26.675)], .5)
        tr(net,[(vx,26.35),(cap_x,26.55),pos(cap,1)], .5)
    tr('VBAT_PROTECTED',[pos('C3',1),pos('C4',1)],1.0)

    # Bulk pads receive adjacent, not in-paste, via pairs.
    for ref, net, vx in [('C6','VBAT_PROTECTED',95.4),('C7','+3V3',70.4)]:
        tr(net,[pos(ref,1),(vx,19.8)],1.0)
        for yy in ([19.1,20.5,21.2] if ref == 'C7' else [19.1,20.5]):
            tr(net,[(vx,19.8),(vx,yy)],.6)
            via(net,(vx,yy))
        for xx in [pos(ref,2)[0]-.7,pos(ref,2)[0]+.7]:
            gvia(ref,2,(xx,12.0),.6)
    tr('VBAT_PROTECTED',[(95.4,19.1),(95.4,20.5),(92.0,23.9),(90.0,23.9),(87.55,26.35),(84.15,26.35)],1.5,pcb.B_Cu)
    tr('+3V3',[(70.4,19.1),(70.4,22.0),(75.85,25.3),(75.85,26.675)],1.5,pcb.B_Cu)

    # Power-ground legs enter their ground plane next to the capacitors.
    for ref,x in [('C3',85.2),('C4',87.4),('C8',74.8)]:
        gvia(ref,2,(x-.35,29.15),.4)
        gvia(ref,2,(x+.35,29.15),.4)
    gvia('C9',2,(72.8,29.6),.3)
    tr('+3V3',[pos('C9',1),(70.4,28.7)],.6)
    via('+3V3',(70.4,28.7));tr('+3V3',[(70.4,22.0),(70.4,28.7)],1.0,pcb.B_Cu)
    tr('+3V3',[(70.4,28.7),(68.0,28.7)],1.6,pcb.B_Cu)

    # Keep drills outside the exposed-pad mask/paste: ordinary prototype
    # fabrication is not assumed to supply filled/capped via-in-pad. Wide
    # copper strips take heat to nine adjacent ground-plane vias. This needs
    # thermal measurement and is not the datasheet's in-pad-via thetaJA board.
    for x in [79,80,81]:
        tr('GND',[(x,24),(x,22.1)],.8)
        tr('GND',[(x,30.3),(x,32.7)],.8)
        for y in [22.1,31.9,32.7]:via('GND',(x,y),.6,.3)
    for pin in [4,9,20,25]:
        x,y=pos('U1',pin)
        tr('GND',[(x,y),(80,y)],.3)
    tr('GND',[pos('U1',14),(79.0,31.225),(80,30.5)],.3)
    tr('GND',[pos('U1',28),(80,22.775),(80,24)],.3)

    # VCC bootstrap supply, quiet compensation/feedback, and RT.
    tr('REG_VCC',[pos('U1',16),(83.7,30.575),(84.1,31.2),pos('C11',1)],.3)
    tr('REG_VCC',[pos('U1',15),(83.7,31.225),(84.1,31.2)],.3)
    tr('REG_VCC',[pos('C11',1),(84.75,37),pos('D1',1)],.4)
    gvia('C11',2,(86.65,34.2),.4)
    tr('REG_VCC',[pos('U1',11),(76.15,29.275)],.2);via('REG_VCC',(76.15,29.275),.45,.2)
    tr('REG_VCC',[(76.15,29.275),(76.15,33.5),(83.5,33.5),(84.0,33.2)],.3,pcb.B_Cu)
    via('REG_VCC',(84.0,33.2),.45,.2);tr('REG_VCC',[(84.0,33.2),pos('C11',1)],.3)
    tr('REG_RT',[pos('U1',17),(83.8,29.925),pos('R5',1)],.2)
    gvia('R5',2,(87.3,30.3),.2)
    tr('REG_FB',[pos('U1',12),(74.425,29.925),pos('R2',2),pos('R3',1)],.2)
    tr('REG_VC',[pos('U1',13),(76.0,30.575),(76.0,32.1),pos('R4',1)],.2)
    tr('COMP_RC',[pos('R4',2),pos('C10',1)],.2)
    tr('GND',[pos('R3',2),(75.4,38.275),pos('C10',2),(80,38.275),(80,30.5)],.3)
    tr('+3V3',[pos('C9',1),(71.625,29.3),(71.625,32.0),pos('R2',1)],.2)
    tr('+3V3',[pos('R6',1),(69.175,28.7),(70.4,28.7)],.3)
    tr('PWR_GOOD',[pos('U1',10),(76.15,28.625)],.2);via('PWR_GOOD',(76.15,28.625),.45,.2)
    tr('PWR_GOOD',[(76.15,28.625),(76.15,28.4),(71.8,28.4),(71.8,31.2),(70.825,32.2)],.2,pcb.B_Cu)
    via('PWR_GOOD',(70.825,32.2),.45,.2);tr('PWR_GOOD',[(70.825,32.2),pos('R6',2)],.2)
    tr('+3V3',[pos('D1',2),(82.35,37.7)],.4);via('+3V3',(82.35,37.7))
    tr('+3V3',[(82.35,37.7),(68,37.7),(68,28.7)],.8,pcb.B_Cu)

    # Battery connector/fuse/reverse PMOS. The three source pins are tied with
    # short individual escapes before the wide branch and two vias.
    tr('BAT_PLUS',[pos('J1',1),(88,37.0),(96.4,37.0),pos('F1',1)],1.5)
    tr('BAT_FUSED',[pos('F1',2),(96.4,31.2),pos('Q1',5)],1.5)
    for pin in [1,2,3]:
        x,y=pos('Q1',pin);tr('VBAT_PROTECTED',[(x,y),(90.0,y)],.3)
    tr('VBAT_PROTECTED',[(90.0,28.725),(90.0,30.025)],.6)
    for y in [28.725,29.425]:via('VBAT_PROTECTED',(90.0,y))
    tr('VBAT_PROTECTED',[(90.0,29.425),(90.0,26.35),(87.55,26.35)],1.5,pcb.B_Cu)
    tr('REV_GATE',[pos('Q1',4),(91.2,31.3),(91.85,31.5)],.2);via('REV_GATE',(91.85,31.5),.45,.2)
    tr('REV_GATE',[(91.85,31.5),(91.85,25.375)],.2,pcb.B_Cu)
    via('REV_GATE',(91.85,25.375),.45,.2);tr('REV_GATE',[(91.85,25.375),pos('R1',1)],.2)
    gvia('R1',2,(93.0,27.1),.2)
    for xy in [(90.4,40),(93.5,40)]:gvia('J1',2,xy,1.0)
    tr('VBAT_PROTECTED',[pos('C5',1),(90.0,30.025)],.4)
    gvia('C5',2,(88.0,30.85),.3)
    tr('VBAT_PROTECTED',[pos('U1',19),(83.9,28.625)],.3)
    via('VBAT_PROTECTED',(83.9,28.625),.55,.3)
    tr('VBAT_PROTECTED',[(83.9,28.625),(84.15,26.675)],.6,pcb.B_Cu)

    # User OFF and UVLO remain quiet signals; do not add capacitance to RUN.
    tr('REG_RUN',[pos('U1',18),(84.05,29.4)],.2);via('REG_RUN',(84.05,29.4),.45,.2)
    tr('VBAT_PROTECTED',[pos('R7',1),(88.3,32.6)],.3);via('VBAT_PROTECTED',(88.3,32.6))
    tr('VBAT_PROTECTED',[(88.3,32.6),(90.0,30.9),(90.0,29.425)],.6,pcb.B_Cu)
    tr('REG_RUN',[pos('R7',2),(89.7,35.025),(91.3,33.375),pos('R8',1),pos('C12',1)],.2)
    tr('REG_RUN',[pos('R7',2),(88.3,35.75)],.2);via('REG_RUN',(88.3,35.75),.45,.2)
    tr('REG_RUN',[(84.05,29.4),(85.4,31.3),(88.3,35.5),(88.3,35.75)],.2,pcb.B_Cu)
    tr('GND',[pos('R8',2),pos('C12',2),(92.05,35.1)],.3);via('GND',(92.05,35.1))
    gvia('J2',2,(98.25,26.54),.4)
    tr('REG_RUN',[pos('J2',1),(98.8,24),(98.8,36),(88.3,35.5)],.2,pcb.B_Cu)
    return {**counts, 'recommended_3v3_trunk_anchor': [68.0,28.7],
            'c7_positive_vias': [[70.4,19.1],[70.4,20.5],[70.4,21.2]],
            'requirements': requirements()}
