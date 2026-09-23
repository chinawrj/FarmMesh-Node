#!/usr/bin/env python3
"""Placement-only C5 islands for the 100 x 100 mm A1 board.

Public API (stdlib only):
    placements(manifest_path=None) -> {reference: (x_mm, y_mm, kicad_angle_deg)}
    suggestions(manifest_path=None) -> ground-via / decoupling / access metadata

PCB API (pcbnew required):
    route(board, footprints, nets=None, manifest_path=None) -> routing summary
    Adds local copper to the supplied in-memory board; never loads/saves a PCB.
    footprints is {reference: FOOTPRINT}. nets may be a short-name or full-name
    map; exact NetInfo is read from actual pads, so hierarchical names are safe.

Coordinates are KiCad front view (+x right, +y down). Nothing here writes a PCB
or changes the schematic. RP-driven series resistors and RP-side VALID pulls
are deliberately excluded. Run --validate with KiCad's Python to check actual
footprint courtyards; this does not check the rest of the motherboard or routes.
"""
import argparse
import json
import math
import os
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
MODULES = {
    'A': ('U201', 20.0, 20.0, 90.0),
    'B': ('U301', 20.0, 80.0, 180.0),
    'C': ('U401', 80.0, 80.0, 270.0),
}
MOUNTING_HOLES = ((5.0, 5.0), (95.0, 5.0), (5.0, 95.0), (95.0, 95.0))
MOUNTING_KEEP_OUT_RADIUS = 3.5  # Project allowance for M3 head/washer/tool.

# Local coordinates relative to the unrotated module. Left/right series parts
# are individually staggered to avoid 0603 courtyard clashes at 1.27 mm pitch.
SOURCE_SERIES = {
    'TX_D0': (-11.6, -2.8),
    'TX_D1': (-11.6, -1.0),
    'TX_D2': (-11.6, 6.1),
    'TX_D3': (-11.6, 7.9),
    'TX_CLK': (11.6, 4.85),
    'TX_VALID': (11.6, 6.55),
    'RX_CLK': (11.6, 0.0),
}


def _manifest(path=None):
    return json.loads(Path(path or BASE / 'design-manifest.json').read_text())


def _nets(component):
    return {p['net'] for p in component['pins'].values() if p.get('net')}


def _transform(module, local):
    _, x, y, angle = module
    lx, ly, local_angle = local
    r = math.radians(angle)
    return (round(x + lx * math.cos(r) + ly * math.sin(r), 4),
            round(y - lx * math.sin(r) + ly * math.cos(r), 4),
            round((angle + local_angle) % 360, 4))


def _resolve(path=None):
    manifest = _manifest(path)
    by_ref = {c['reference']: c for c in manifest}
    result, roles = {}, {}
    for letter, module in MODULES.items():
        module_ref = module[0]
        if module_ref not in by_ref or 'ESP32-C5-WROOM-1U' not in by_ref[module_ref]['value']:
            raise ValueError('Expected C5 module ' + module_ref)
        sheet = by_ref[module_ref]['sheet']
        parts = [c for c in manifest if c['sheet'] == sheet]

        def one(role, prefix, nets=None, value_prefix=None):
            found = [c for c in parts if c['reference'].startswith(prefix)
                     and (nets is None or _nets(c) == set(nets))
                     and (value_prefix is None or c['value'].startswith(value_prefix))]
            if len(found) != 1:
                raise ValueError('{} {}: expected one part, got {}'.format(letter, role, [c['reference'] for c in found]))
            roles[letter + '_' + role] = found[0]['reference']
            return found[0]

        def place(component, x, y, angle):
            result[component['reference']] = _transform(module, (x, y, angle))

        # Select by both endpoints, not by contiguous reference-number ranges.
        result[module_ref] = module[1:]
        roles[letter + '_module'] = module_ref
        for signal, (x, y) in SOURCE_SERIES.items():
            net = letter + '_' + signal
            part = one(signal + '_series', 'R', (net, net + '_C5'), '22R')
            source_is_pad1 = part['pins']['1']['net'] == net + '_C5'
            # Pad facing the module carries the C5-side net.
            angle = (180 if x < 0 else 0) if source_is_pad1 else (0 if x < 0 else 180)
            place(part, x, y, angle)

        for role, value, x, y in (
            ('decouple_100n', '100n', -11.6, -7.6),
            ('decouple_22u', '22u', -15.6, -7.8),
            ('bulk_100u', '100u', -16.0, -13.3),
        ):
            place(one(role, 'C', ('+3V3', 'GND'), value), x, y, 180)
        place(one('en_pull', 'R', ('+3V3', letter + '_EN')), -11.6, -5.5, 0)
        place(one('en_cap', 'C', (letter + '_EN', 'GND')), -15.2, -5.5, 180)
        place(one('boot_pull', 'R', ('+3V3', letter + '_BOOT')), 11.6, 8.7, 180)
        place(one('strap27_pull', 'R', ('+3V3', letter + '_STRAP27')), 11.6, 2.6, 180)
        place(one('rx_valid_pull', 'R', (letter + '_RX_VALID_C5', 'GND')), 11.6, -2.6, 0)
        # A's RESET is pulled back 1.5 mm to clear the RP BOOTSEL resistor R103.
        place(one('reset_button', 'SW', (letter + '_EN', 'GND')), -6.5, 14.5 if letter == 'A' else 16.0, 0)
        place(one('boot_button', 'SW', (letter + '_BOOT', 'GND')), 6.5, 16.0, 0)
        place(one('uart_header', 'J', ('GND', '+3V3', letter + '_UART_TX',
                                     letter + '_UART_RX', letter + '_EN', letter + '_BOOT')),
              16.0, -8.0, 0)

        placed_here = {r for r in result if by_ref[r]['sheet'] == sheet}
        expected_exclusions = set()
        for signal in ('RX_D0', 'RX_D1', 'RX_D2', 'RX_D3', 'RX_VALID'):
            net = letter + '_' + signal
            expected_exclusions.add(one(signal + '_rp_series', 'R', (net, net + '_C5'), '22R')['reference'])
        expected_exclusions.add(one('tx_valid_rp_pull', 'R', (letter + '_TX_VALID', 'GND'))['reference'])
        actual_exclusions = {c['reference'] for c in parts if not c['reference'].startswith('#')} - placed_here
        if actual_exclusions != expected_exclusions:
            raise ValueError('Unclassified {} radio components: {}'.format(letter, actual_exclusions ^ expected_exclusions))
    return result, roles, by_ref


def placements(manifest_path=None):
    """Return 57 component placements; no PCB imports or side effects."""
    return _resolve(manifest_path)[0]


def suggestions(manifest_path=None):
    """Return advisory GND geometry and assembly envelopes for the layout author.

    Via positions require actual-board DRC and zone connectivity verification.
    The antenna access envelope is provisional, not an RF keepout prescription.
    """
    result, roles, _ = _resolve(manifest_path)
    answer = {}
    for letter, module in MODULES.items():
        def point(x, y):
            return _transform(module, (x, y, 0))[:2]
        cx, cy = 0.8298, -0.322
        outer_vias = [point(cx + dx, cy + dy) for dx, dy in
                      ((-3.15, -3.15), (0, -3.15), (3.15, -3.15), (-3.15, 0),
                       (3.15, 0), (-3.15, 3.15), (0, 3.15), (3.15, 3.15))]
        answer[letter] = {
            'module': module[0],
            'power_pad2_xy_mm': point(-8.75, -7.64),
            'decoupling': {roles[letter + '_' + name]: result[roles[letter + '_' + name]]
                           for name in ('decouple_100n', 'decouple_22u', 'bulk_100u')},
            'ground_vias': {
                'net': 'GND', 'drill_mm': .3, 'diameter_mm': .6,
                'tent_front': True, 'tent_back': True, 'paste': False,
                'ep_gap_xy_mm': [], 'ep_outer_ring_xy_mm': outer_vias,
                'ep_process': 'No holes within the nine EP paste/mask windows or their gaps. Eight outer vias join solid top EP ground to inner ground; avoids reliance on tenting immediately beside exposed mask openings.',
                'peripheral_xy_mm': [point(-7.8, -9.8), point(7.8, -9.8),
                                     point(1.46, -12.1), point(4.0, -12.1)],
                'decoupling_advisory': 'Add a ground via immediately beside each capacitor GND pad; keep supply routes wide and short.',
            },
            'ant1': {'xy_mm': point(6.0, -8.22), 'provisional_access_square_mm': 8,
                     'provisional_clear_height_mm': 7, 'provisional_cable_corridor_width_mm': 3,
                     'note': 'Confirm chosen coax plug/tool/bend radius; no PCB-antenna void is imposed on the 1U module.'},
            'source_series_refs': [roles[letter + '_' + s + '_series'] for s in SOURCE_SERIES],
            'excluded_rp_source_series_refs': [roles[letter + '_' + s + '_rp_series']
                                                for s in ('RX_D0', 'RX_D1', 'RX_D2', 'RX_D3', 'RX_VALID')],
            'excluded_rp_receiver_pull': roles[letter + '_tx_valid_rp_pull'],
        }
    return answer


def route(board, footprints, nets=None, manifest_path=None):
    """Add self-contained radio critical routes to an in-memory pcbnew board.

    Uses the *actual pad* net objects; ``nets`` is accepted for compatibility with
    the main generator's by_short/full-name maps but is not needed for lookup.
    No RP-driven resistor, RP receiver pull, UART signal or debug button route
    is added. Signal routes remain on F.Cu. B.Cu power trunks may land on each
    returned pair of +3V3 feed vias. Zones still need board-wide fill/DRC.
    """
    import pcbnew
    _, roles, manifest = _resolve(manifest_path)
    counts = {'segments_added': 0, 'vias_added': 0, 'zones_added': 0}
    power_feeds = {}

    def mm(v):
        return pcbnew.ToMM(v)

    def vector(p):
        return pcbnew.VECTOR2I(pcbnew.FromMM(p[0]), pcbnew.FromMM(p[1]))

    def pad(ref, number):
        return next(p for p in footprints[ref].Pads() if p.GetNumber() == str(number))

    def add_segments(net, points, width):
        for start, end in zip(points, points[1:]):
            a, b = vector(start), vector(end)
            if a == b:
                continue
            already = False
            for t in board.GetTracks():
                if isinstance(t, pcbnew.PCB_VIA) or t.GetLayer() != pcbnew.F_Cu:
                    continue
                if (t.GetStart() == a and t.GetEnd() == b) or (t.GetStart() == b and t.GetEnd() == a):
                    if t.GetNetCode() != net.GetNetCode():
                        raise ValueError('Existing different-net track at radio route')
                    already = True
                    break
            if not already:
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(a); t.SetEnd(b)
                t.SetWidth(pcbnew.FromMM(width)); t.SetLayer(pcbnew.F_Cu)
                t.SetNet(net); board.Add(t)
                counts['segments_added'] += 1

    def add_via(net, p):
        pos = vector(p)
        for t in board.GetTracks():
            if isinstance(t, pcbnew.PCB_VIA) and t.GetPosition() == pos:
                if t.GetNetCode() != net.GetNetCode():
                    raise ValueError('Existing different-net via at radio route')
                return
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pos); v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetWidth(pcbnew.FromMM(.6)); v.SetDrill(pcbnew.FromMM(.3))
        v.SetFrontTentingMode(pcbnew.TENTING_MODE_TENTED)
        v.SetBackTentingMode(pcbnew.TENTING_MODE_TENTED)
        v.SetNet(net); board.Add(v)
        counts['vias_added'] += 1

    for letter, proposal in MODULES.items():
        module_ref = proposal[0]
        module = footprints[module_ref]
        centre = module.GetPosition()
        angle = math.radians(module.GetOrientationDegrees())
        c, s = math.cos(angle), math.sin(angle)

        def global_xy(p):
            return (round(mm(centre.x) + p[0] * c + p[1] * s, 6),
                    round(mm(centre.y) - p[0] * s + p[1] * c, 6))

        def local_pad(ref, number):
            p = pad(ref, number).GetPosition()
            dx, dy = mm(p.x - centre.x), mm(p.y - centre.y)
            return (round(dx * c - dy * s, 6), round(dx * s + dy * c, 6))

        def wire(net, points, width=.25):
            add_segments(net, [global_xy(p) for p in points], width)

        def fanout(module_pin, ref, resistor_pin):
            a, b = local_pad(module_ref, module_pin), local_pad(ref, resistor_pin)
            sign = -1 if a[0] < 0 else 1
            corner = (b[0] - sign * abs(b[1] - a[1]), a[1])
            source_net = pad(module_ref, module_pin).GetNet()
            if pad(ref, resistor_pin).GetNetCode() != source_net.GetNetCode():
                raise ValueError('Net mismatch at {} pad{}'.format(ref, resistor_pin))
            wire(source_net, [a, corner, b])

        def role(name):
            return roles[letter + '_' + name]

        gnd = pad(module_ref, 1).GetNet()
        supply = pad(module_ref, 2).GetNet()
        for signal in SOURCE_SERIES:
            ref = role(signal + '_series')
            logical_net = letter + '_' + signal + '_C5'
            mn = next(n for n, p in manifest[module_ref]['pins'].items() if p.get('net') == logical_net)
            rn = next(n for n, p in manifest[ref]['pins'].items() if p.get('net') == logical_net)
            fanout(mn, ref, rn)

        # 0.8 mm supply route: enter 100 nF first, branch around its GND pad
        # toward 22 uF and bulk. An inline route across cap pad2 would short GND.
        small, medium, bulk = role('decouple_100n'), role('decouple_22u'), role('bulk_100u')
        psmall, pmedium, pbulk = [local_pad(ref, 1) for ref in (small, medium, bulk)]
        wire(supply, [local_pad(module_ref, 2), psmall], .8)
        wire(supply, [psmall, (psmall[0], -9.6), (pmedium[0], -9.6), pmedium], .8)
        wire(supply, [(pbulk[0], -9.6), pbulk], .8)
        feed_local = [(-12.6, -15.15), (-13.4, -15.15)]
        wire(supply, [pbulk, (pbulk[0], -15.15)], .8)
        for p in feed_local:
            wire(supply, [(pbulk[0], -15.15), p], .8)
            add_via(supply, global_xy(p))
        power_feeds[letter] = {'net': supply.GetNetname(), 'xy_mm': [global_xy(p) for p in feed_local],
                               'drill_mm': .3, 'diameter_mm': .6,
                               'purpose': 'Pair of +3V3 through vias for the B.Cu star-feed trunk; verify current/thermal design on final stack.'}

        en_pull, en_cap = role('en_pull'), role('en_cap')
        fanout(3, en_pull, 2)
        en_net = pad(module_ref, 3).GetNet()
        ep, ec = local_pad(en_pull, 2), local_pad(en_cap, 1)
        wire(en_net, [ep, (ep[0], -4.05), (ec[0], -4.05), ec])
        wire(supply, [local_pad(en_pull, 1), (-13.4, -5.5), (-13.4, -6.5),
                      (pmedium[0], -6.5), pmedium], .3)
        fanout(15, role('boot_pull'), 2)
        fanout(18, role('strap27_pull'), 2)
        fanout(23, role('rx_valid_pull'), 1)

        # A low-current DC branch inside the module perimeter, outside its EP,
        # reaches the right-side strap pulls. No signal layer transitions.
        wire(supply, [local_pad(module_ref, 2), (-6.6, -7.64), (-6.6, -5.4),
                      (6.5, -5.4), (6.5, 11.8), (13.6, 11.8), (13.6, 2.6)], .3)
        for name in ('boot_pull', 'strap27_pull'):
            p = local_pad(role(name), 1)
            wire(supply, [p, (13.6, p[1])], .3)
        uart_power = local_pad(role('uart_header'), 6)
        wire(supply, [(13.6, uart_power[1]), uart_power], .3)

        # Vias beside (never in) capacitor paste openings and receiving pull.
        grounding = [(small, (local_pad(small, 2)[0], -8.65)),
                     (medium, (local_pad(medium, 2)[0], -9.25)),
                     (bulk, (local_pad(bulk, 2)[0], -15.15)),
                     (en_cap, (local_pad(en_cap, 2)[0], -4.4)),
                     (role('rx_valid_pull'), (local_pad(role('rx_valid_pull'), 2)[0], -3.8))]
        for ref, p in grounding:
            wire(gnd, [local_pad(ref, 2), p], .4)
            add_via(gnd, global_xy(p))
        ground_pad_vias = [(1, (-7.8, -9.8)), (28, (7.8, -9.8)),
                           (32, (1.46, -12.1)), (30, (4.0, -12.1))]
        for num, p in ground_pad_vias:
            wire(gnd, [local_pad(module_ref, num), p], .4)
            add_via(gnd, global_xy(p))
        cx, cy = .8298, -.322
        # Keep the complete 4.7 mm EP window envelope hole-free. Vias between
        # 0.4 mm gaps cannot provide a robust mask web for the chosen fab rules.
        ep_vias = [(cx + dx, cy + dy) for dx, dy in
                    ((-3.15, -3.15), (0, -3.15), (3.15, -3.15), (-3.15, 0),
                     (3.15, 0), (-3.15, 3.15), (0, 3.15), (3.15, 3.15))]
        for p in ep_vias:
            add_via(gnd, global_xy(p))

        # Solid EP connection to local top ground, over continuous L2 ground.
        # Higher priority than the board-wide top pour; no thermal spokes here.
        zone_name = 'C5-{} local EP ground'.format(letter)
        if not any(z.GetZoneName() == zone_name for z in board.Zones()):
            z = pcbnew.ZONE(board)
            z.SetZoneName(zone_name); z.SetLayer(pcbnew.F_Cu); z.SetNet(gnd)
            z.SetAssignedPriority(10); z.SetLocalClearance(pcbnew.FromMM(.2))
            z.SetMinThickness(pcbnew.FromMM(.15)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
            outline = z.Outline(); outline.NewOutline()
            for p in ((-8.2, -10.4), (8.2, -10.4), (8.2, 10.4), (-8.2, 10.4)):
                q = vector(global_xy(p)); outline.Append(q.x, q.y)
            board.Add(z); counts['zones_added'] += 1
    return dict(counts, power_feed_vias=power_feeds,
                boundary='Only local C5 critical copper was added. Fill all zones and run complete board DRC before release.')


def validate(manifest_path=None, kicad_share=None):
    """Check actual F.CrtYd rectangles, board bounds, M3 allowance, source-pad proximity.

    Requires pcbnew. No board is loaded or saved. Returns a JSON-serializable
    report and raises ValueError on clearance/coverage/source-placement failure.
    """
    import pcbnew
    result, roles, by_ref = _resolve(manifest_path)
    share = Path(kicad_share or os.environ.get('KICAD_SHARE',
                 '/Users/rjwang/Applications/KiCad/KiCad.app/Contents/SharedSupport'))
    footprints, boxes = {}, {}
    for ref, (x, y, angle) in result.items():
        lib, name = by_ref[ref]['footprint'].split(':', 1)
        folder = BASE / (lib + '.pretty') if lib == 'FarmMesh' else share / 'footprints' / (lib + '.pretty')
        f = pcbnew.FootprintLoad(str(folder), name)
        if f is None:
            raise ValueError('Cannot load footprint for ' + ref)
        f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        f.SetOrientationDegrees(angle)
        courtyard = [s.GetBoundingBox() for s in f.GraphicalItems() if s.GetLayer() == pcbnew.F_CrtYd]
        if not courtyard:
            raise ValueError('No front courtyard for ' + ref)
        box = (min(pcbnew.ToMM(b.GetLeft()) for b in courtyard),
               min(pcbnew.ToMM(b.GetTop()) for b in courtyard),
               max(pcbnew.ToMM(b.GetRight()) for b in courtyard),
               max(pcbnew.ToMM(b.GetBottom()) for b in courtyard))
        boxes[ref] = box
        footprints[ref] = f
    errors = []
    for ref, (l, t, r, b) in boxes.items():
        if min(l, t) < 0 or max(r, b) > 100:
            errors.append('Board edge: {} {}'.format(ref, (l, t, r, b)))
        for hx, hy in MOUNTING_HOLES:
            dx, dy = max(l - hx, 0, hx - r), max(t - hy, 0, hy - b)
            if math.hypot(dx, dy) < MOUNTING_KEEP_OUT_RADIUS:
                errors.append('M3 allowance: {} at ({}, {})'.format(ref, hx, hy))
    refs = list(boxes)
    for i, ra in enumerate(refs):
        a = boxes[ra]
        for rb in refs[i + 1:]:
            b = boxes[rb]
            if min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1]):
                errors.append('Courtyard overlap: {} / {}'.format(ra, rb))
    distances = {}
    for letter, module in MODULES.items():
        m = by_ref[module[0]]
        mpads = {p.GetNumber(): p for p in footprints[module[0]].Pads()}
        for signal in SOURCE_SERIES:
            ref = roles[letter + '_' + signal + '_series']
            net = letter + '_' + signal + '_C5'
            mn = next(n for n, p in m['pins'].items() if p.get('net') == net)
            rn = next(n for n, p in by_ref[ref]['pins'].items() if p.get('net') == net)
            rp = next(p for p in footprints[ref].Pads() if p.GetNumber() == rn)
            p, q = mpads[mn].GetPosition(), rp.GetPosition()
            d = math.hypot(pcbnew.ToMM(p.x - q.x), pcbnew.ToMM(p.y - q.y))
            distances[ref] = round(d, 3)
            if d > 3.0:
                errors.append('Source pad farther than 3 mm: {} {:.3f}'.format(ref, d))
    if errors:
        raise ValueError('\n'.join(errors))
    return {'status': 'pass', 'component_count': len(result), 'source_series_count': len(distances),
            'max_source_pad_to_resistor_pad_mm': max(distances.values()),
            'source_pad_to_resistor_pad_mm': distances, 'courtyard_bounds_mm': boxes,
            'limits': 'Placement-only check of radio islands, M3 3.5mm-radius allowance and 100mm square. No other board parts, trace routing, zones, RF or full board DRC verified.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest')
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--suggestions', action='store_true')
    parser.add_argument('--kicad-share')
    args = parser.parse_args()
    output = validate(args.manifest, args.kicad_share) if args.validate else suggestions(args.manifest) if args.suggestions else placements(args.manifest)
    print(json.dumps(output, indent=2))
