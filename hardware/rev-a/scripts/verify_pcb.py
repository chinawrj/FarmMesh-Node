#!/usr/bin/env python3
"""Read-only independent PCB checks using KiCad's bundled Python.

The board is never saved or zone-filled. The JSON pins its input hashes and
separates automated geometric/net-assignment checks from expert/bench checks.
Run after final routing and zone fill:
  <KiCad Python> scripts/verify_pcb.py
Options: --board FILE --output FILE --share KICAD_SHARED_SUPPORT
This is not a replacement for KiCad DRC/ERC or manufacturing acceptance.
"""
import argparse
import collections
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parents[1]
EXPECTED_COMPONENTS = 164
GLOBAL_NETS = {'GND', '+3V3', 'VBAT_PROTECTED', 'PWR_GOOD', 'BAT_SENSE',
              'RP_USB_DM', 'RP_USB_DP', 'USB_VBUS_SENSE', 'CORE_1V1', 'RP_RUN'}
SIGNALS = ['TX_D0', 'TX_D1', 'TX_D2', 'TX_D3', 'TX_CLK', 'TX_VALID',
           'RX_D0', 'RX_D1', 'RX_D2', 'RX_D3', 'RX_CLK', 'RX_VALID']
EP_PADS = {'U101': '81', 'U1': '29', 'U201': '29', 'U301': '29', 'U401': '29'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean_net(name):
    """The source export contains slash characters inside sheet/pin names."""
    name = name.replace(' / ', ' {slash} ')
    return name.replace('/ADC', '{slash}ADC') if name.startswith('unconnected-') else name


def result(errors, **details):
    return dict(status='fail' if errors else 'pass', errors=errors, **details)


def close(a, b, tolerance=.000003):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a-b) <= tolerance
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(close(x, y, tolerance) for x, y in zip(a, b))
    return a == b


def adjusted_paste_pad(pad, layer):
    """Detached pad matching paste plotting dimensions; original is untouched.

    pcbnew GetEffectiveShape does NOT apply solder-paste margins. Mirror KiCad
    plot_board_layers.cpp for circle/oval/rectangle/roundrect aperture sizing,
    then query the resulting effective shape. Nonzero-margin custom/chamfered
    geometries fail explicitly until their plotting rules are implemented.
    Source: https://docs.kicad.org/doxygen/plot__board__layers_8cpp_source.html
    """
    import pcbnew as p
    margin=pad.GetSolderPasteMargin(layer)
    if not margin.x and not margin.y:return pad
    size=pad.GetSize(layer)
    plotted=p.VECTOR2I(size.x+2*margin.x,size.y+2*margin.y)
    if plotted.x<=0 or plotted.y<=0:return None
    shape=pad.GetShape(layer)
    supported=(p.PAD_SHAPE_CIRCLE,p.PAD_SHAPE_OVAL,p.PAD_SHAPE_RECT,p.PAD_SHAPE_ROUNDRECT)
    if shape not in supported:raise ValueError('Nonzero paste margin on unsupported pad shape '+str(shape))
    copy=pad.Duplicate()
    old_radius=pad.GetRoundRectCornerRadius(layer) if shape==p.PAD_SHAPE_ROUNDRECT else 0
    old_ratio=pad.GetRoundRectRadiusRatio(layer)
    copy.SetSize(layer,plotted)
    if shape==p.PAD_SHAPE_RECT and margin.x>0:
        copy.SetShape(layer,p.PAD_SHAPE_ROUNDRECT)
        copy.SetRoundRectRadiusRatio(layer,min(.5,margin.x/min(plotted.x,plotted.y)))
    elif shape==p.PAD_SHAPE_ROUNDRECT:
        ratio=min(.5,max(0,old_radius+margin.x)/min(plotted.x,plotted.y)) if margin.x==margin.y else old_ratio
        copy.SetRoundRectRadiusRatio(layer,ratio)
    return copy


def run(board_path, share):
    import pcbnew as p
    import wx
    app = wx.App(False)
    wx.Log.SetLogLevel(0)
    mm = p.FromMM
    to_mm = lambda value: round(p.ToMM(value), 9)
    xy = lambda point: [to_mm(point.x), to_mm(point.y)]
    vector = lambda point: p.VECTOR2I(mm(point[0]), mm(point[1]))
    board_path = board_path.resolve()
    input_paths = {'pcb': board_path, 'manifest': BASE/'design-manifest.json',
                   'xml_netlist': BASE/'reports/netlist.xml'}
    before_hashes = {name: digest(path) for name, path in input_paths.items()}
    manifest = json.loads(input_paths['manifest'].read_text())
    components = {c['reference']: c for c in manifest
                  if not c['reference'].startswith('#') and c.get('footprint')}
    xml = ET.parse(input_paths['xml_netlist']).getroot()
    b = p.LoadBoard(str(board_path))
    fps = list(b.GetFootprints())
    by_ref = {f.GetReference(): f for f in fps}
    report = {
        'schema_version': 1,
        'generated_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'kicad_version': p.Version(),
        'board': board_path.name,
        'read_only': True,
        'input_sha256': before_hashes,
        'automated_checks': {},
        'expert_review_required': [
            'Complete KiCad DRC/ERC, including shorts, clearances, schematic parity and zero unrouted connections, is a separate release gate.',
            'Ground filled-polygon connectivity and area do not prove adequate return-path neck widths, stitching, EMI performance or every high-speed return path.',
            'USB trunk dimensions are geometric checks for the specified straight coupled span only; connector/switch/ESD/via/resistor escapes are not claimed to maintain the same impedance. Fabricator stackup/impedance acceptance and USB measurements remain required.',
            'Source-series distance is a placement measurement, not timing/SI sign-off. Confirm drive strengths, chosen clocks, crosstalk, skew and ringing on hardware; firmware remains unimplemented.',
            'EP checks prove no finished drill geometry intersects the defined paste apertures or EP bounding envelope. They do not certify solder-mask tenting, stencil/reflow yield, thermal resistance or fabricator process capability.',
            'Inspect buck switching-current loops, crystal/QSPI coupling, RP reset/boot behavior, connector/mechanical access and external dual-band antenna/coax assembly clearances.',
            'RF coexistence, antenna placement in the enclosure, output power, thermal rise and multi-radio performance require measurements; this report is not a fabrication-release authorization.'
        ],
    }
    checks = report['automated_checks']
    # Ref and footprint provenance: independent of the PCB-generation script.
    counts = collections.Counter(f.GetReference() for f in fps)
    errors = []
    if len(fps) != EXPECTED_COMPONENTS or len(components) != EXPECTED_COMPONENTS:
        errors.append({'expected_count': EXPECTED_COMPONENTS, 'pcb': len(fps), 'manifest': len(components)})
    if set(by_ref) != set(components):
        errors.append({'missing_references': sorted(set(components)-set(by_ref)),
                       'unexpected_references': sorted(set(by_ref)-set(components))})
    duplicates = sorted(ref for ref, n in counts.items() if n != 1)
    if duplicates: errors.append({'duplicate_references': duplicates})
    rear = sorted(f.GetReference() for f in fps if f.IsFlipped() or f.GetLayer() != p.F_Cu)
    if rear: errors.append({'non_front_footprints': rear})
    checks['component_inventory'] = result(errors, expected_count=EXPECTED_COMPONENTS,
                                          actual_count=len(fps), manifest_count=len(components),
                                          all_front=not rear)

    # XML and manifest topology are compared as node sets, never only net labels.
    xml_node_net, xml_groups = {}, collections.defaultdict(set)
    topology_errors = []
    for n in xml.findall('./nets/net'):
        name = clean_net(n.get('name'))
        for node in n.findall('node'):
            key = (node.get('ref'), node.get('pin'))
            if key[0] not in components: continue
            if key in xml_node_net: topology_errors.append({'duplicate_xml_node': key})
            xml_node_net[key] = name
            xml_groups[name].add(key)
    expected = collections.defaultdict(set)
    nc_nodes = set()
    for ref, component in components.items():
        for num, pin in component['pins'].items():
            net = pin.get('net')
            if net is None:
                nc_nodes.add((ref, num)); continue
            global_ = net in GLOBAL_NETS or (net.startswith(('A_', 'B_', 'C_')) and not net.endswith('_C5'))
            expected[('global' if global_ else component['sheet'], net)].add((ref, num))
    for key, nodes in expected.items():
        actual = {xml_node_net.get(node) for node in nodes}
        if len(actual) != 1 or None in actual:
            topology_errors.append({'manifest_net': list(key), 'missing_or_split_xml_nodes': sorted(nodes), 'xml_nets': sorted(str(x) for x in actual)})
        else:
            actual_name = next(iter(actual))
            if xml_groups[actual_name] != nodes:
                topology_errors.append({'manifest_net': list(key), 'unexpected_xml_node_difference': sorted(xml_groups[actual_name] ^ nodes)})
    for node in sorted(nc_nodes):
        name = xml_node_net.get(node)
        if name and (not name.startswith('unconnected-') or xml_groups[name] != {node}):
            topology_errors.append({'manifest_no_connect_not_isolated_in_xml': node, 'xml_net': name})
    pcb_node_nets = collections.defaultdict(set)
    copper_regions = 0
    for f in fps:
        for pad in f.Pads():
            if pad.GetNumber():
                pcb_node_nets[(f.GetReference(), pad.GetNumber())].add(pad.GetNetname())
                copper_regions += 1
            elif pad.GetNetCode():
                topology_errors.append({'unnumbered_pad_has_net': f.GetReference(), 'net': pad.GetNetname()})
    for node, nets in sorted(pcb_node_nets.items()):
        expected_name = xml_node_net.get(node, '')
        if nets != {expected_name}:
            topology_errors.append({'node': node, 'xml_net': expected_name, 'pcb_nets': sorted(nets)})
    for node in sorted(set(xml_node_net)-set(pcb_node_nets)):
        topology_errors.append({'xml_node_missing_from_board': node})
    for ref, component in components.items():
        board_nums = {number for r, number in pcb_node_nets if r == ref}
        if board_nums != set(component['pins']):
            topology_errors.append({'reference': ref, 'manifest_pad_number_difference': sorted(board_nums ^ set(component['pins']))})
    checks['pad_net_topology'] = result(topology_errors,
        scope='Pad net assignments and exact node-set parity; physical copper shorts are checked separately by KiCad DRC.',
        manifest_connected_net_groups=len(expected), xml_net_groups=len(xml_groups),
        numbered_pad_regions_checked=copper_regions, unique_numbered_pads_checked=len(pcb_node_nets),
        manifest_no_connect_nodes_checked=len(nc_nodes))

    # Compare every pad, including duplicate EP pads and unnumbered paste apertures.
    # Field text, UUIDs, position and rotation of the whole footprint are ignored.
    def pad_signature(pad, footprint):
        local_angle = (pad.GetOrientationDegrees()-footprint.GetOrientationDegrees()) % 360
        if abs(local_angle-360) < .000001: local_angle = 0
        layers = list(pad.GetLayerSet().Seq())
        signature = {
            'number': pad.GetNumber(), 'local_position_mm': xy(pad.GetFPRelativePosition()),
            'local_angle_deg': round(local_angle, 9), 'size_mm': xy(pad.GetSize()),
            'shape': int(pad.GetShape()), 'attribute': int(pad.GetAttribute()),
            'drill_shape': int(pad.GetDrillShape()), 'drill_mm': xy(pad.GetDrillSize()),
            'offset_mm': xy(pad.GetOffset()), 'trapezoid_delta_mm': xy(pad.GetDelta()),
            'layers': layers, 'roundrect_ratio': pad.GetRoundRectRadiusRatio(),
            'chamfer_ratio': pad.GetChamferRectRatio(), 'chamfer_positions': pad.GetChamferPositions(),
            'anchor_shape': int(pad.GetAnchorPadShape(p.F_Cu)),
            'solder_mask_margin_iu': pad.GetLocalSolderMaskMargin(),
            'solder_paste_margin_iu': pad.GetLocalSolderPasteMargin(),
            'solder_paste_margin_ratio': pad.GetLocalSolderPasteMarginRatio(),
            'local_clearance_iu': pad.GetLocalClearance(),
            'local_zone_connection': pad.GetLocalZoneConnection(),
            'local_thermal_gap_iu': pad.GetLocalThermalGapOverride(),
            'local_thermal_spoke_width_iu': pad.GetLocalThermalSpokeWidthOverride(),
        }
        if pad.GetShape() == p.PAD_SHAPE_CUSTOM:
            # PowerDI3333 pad 5 has custom copper. Compare its effective polygon
            # in pad-local coordinates, including any holes and the anchor.
            poly = pad.GetCustomShapeAsPolygon(p.F_Cu)
            def canonical_contour(contour):
                points = [tuple(contour.CPoint(i)) for i in range(contour.PointCount())]
                if not points: return []
                candidates = []
                for sequence in [points, list(reversed(points))]:
                    candidates.extend(sequence[i:]+sequence[:i] for i in range(len(sequence)))
                return min(candidates)
            signature['custom_shape_polygons_iu'] = sorted([
                [canonical_contour(poly.Outline(i)),
                 sorted(canonical_contour(poly.Hole(i,j)) for j in range(poly.HoleCount(i)))]
                for i in range(poly.OutlineCount())])
        return signature
    libraries, library_hashes, geometry_errors, geometry_rows = {}, {}, [], []
    for ref in sorted(set(by_ref) & set(components)):
        f = by_ref[ref]
        fid = components[ref]['footprint']
        actual_fid = str(f.GetFPID().GetLibNickname()) + ':' + str(f.GetFPID().GetLibItemName())
        if actual_fid != fid:
            geometry_errors.append({'reference': ref, 'manifest_footprint': fid, 'pcb_footprint': actual_fid})
        if fid not in libraries:
            lib, name = fid.split(':', 1)
            folder = BASE/'FarmMesh.pretty' if lib == 'FarmMesh' else share/'footprints'/(lib+'.pretty')
            path = folder/(name+'.kicad_mod')
            original = p.FootprintLoad(str(folder), name)
            if original is None: raise RuntimeError('Cannot load '+str(path))
            libraries[fid] = (original, [pad_signature(q, original) for q in original.Pads()])
            library_hashes[fid] = digest(path)
        _, source = libraries[fid]
        actual = [pad_signature(q, f) for q in f.Pads()]
        remaining = list(source)
        diffs = []
        for sig in actual:
            matched = next((i for i, other in enumerate(remaining)
                            if sig['number'] == other['number'] and close(sig['local_position_mm'], other['local_position_mm'])), None)
            if matched is None:
                diffs.append({'unexpected_pad': sig}); continue
            other = remaining.pop(matched)
            changed = {k: {'library': other[k], 'pcb': sig[k]} for k in sig if not close(sig[k], other[k])}
            if changed: diffs.append({'pad_number': sig['number'], 'local_position_mm': sig['local_position_mm'], 'differences': changed})
        if remaining: diffs.append({'missing_library_pads': remaining})
        if diffs: geometry_errors.append({'reference': ref, 'footprint': fid, 'pad_differences': diffs})
        geometry_rows.append({'reference': ref, 'footprint': fid, 'pad_region_count': len(actual), 'status': 'fail' if diffs else 'pass'})
    checks['library_pad_geometry'] = result(geometry_errors,
        ignored='Fields, UUIDs, board net codes, and whole-footprint placement/rotation; all footprints must remain front-side.',
        positional_tolerance_mm=.000003, footprint_types=len(libraries),
        pad_regions_checked=sum(row['pad_region_count'] for row in geometry_rows), footprints=geometry_rows,
        library_file_sha256=library_hashes)

    # Explicit hole geometry is compared with actual paste polygons, not only via centers.
    holes = []
    for t in b.GetTracks():
        if isinstance(t, p.PCB_VIA):
            center = t.GetPosition(); drill = t.GetDrill()
            holes.append(({'type': 'via', 'position_mm': xy(center), 'drill_mm': to_mm(drill)},
                          p.SHAPE_SEGMENT(center, center, drill)))
    for f in fps:
        for pad in f.Pads():
            drill = pad.GetDrillSize()
            if not drill.x and not drill.y: continue
            angle = math.radians(pad.GetOrientationDegrees())
            dx = max(0, drill.x-drill.y)/2; dy = max(0, drill.y-drill.x)/2
            rx = dx*math.cos(angle)+dy*math.sin(angle)
            ry = -dx*math.sin(angle)+dy*math.cos(angle)
            center = pad.GetPosition()
            aa = p.VECTOR2I(round(center.x-rx), round(center.y-ry))
            zz = p.VECTOR2I(round(center.x+rx), round(center.y+ry))
            holes.append(({'type': 'pad_hole', 'reference': f.GetReference(), 'pad': pad.GetNumber(),
                           'position_mm': xy(center), 'drill_mm': xy(drill)},
                          p.SHAPE_SEGMENT(aa, zz, min(drill.x, drill.y))))
    ep_rows, ep_errors = [], []
    for ref, number in EP_PADS.items():
        if ref not in by_ref:
            ep_errors.append({'missing_reference': ref}); continue
        f = by_ref[ref]
        eps = [q for q in f.Pads() if q.GetNumber() == number and q.IsOnLayer(p.F_Cu)]
        if not eps:
            ep_errors.append({'missing_ep': ref}); continue
        boxes = [q.GetBoundingBox() for q in eps]
        x0 = min(q.GetLeft() for q in boxes); x1 = max(q.GetRight() for q in boxes)
        y0 = min(q.GetTop() for q in boxes); y1 = max(q.GetBottom() for q in boxes)
        envelope = p.SHAPE_POLY_SET(); envelope.NewOutline()
        for point in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]: envelope.Append(*point)
        apertures = []
        for q in f.Pads():
            if not q.IsOnLayer(p.F_Paste): continue
            center = q.GetPosition()
            if not (x0 <= center.x <= x1 and y0 <= center.y <= y1): continue
            aperture=adjusted_paste_pad(q,p.F_Paste)
            if aperture is None:continue
            poly = p.SHAPE_POLY_SET()
            aperture.TransformShapeToPolygon(poly, p.F_Paste, 0, mm(.001), p.ERROR_OUTSIDE)
            apertures.append(poly)
        paste_hits, envelope_hits = [], []
        for detail, shape in holes:
            if envelope.Collide(shape, 0): envelope_hits.append(detail)
            if any(aperture.Collide(shape, 0) for aperture in apertures): paste_hits.append(detail)
        if paste_hits or envelope_hits or not apertures:
            ep_errors.append({'reference': ref, 'paste_hole_intersections': paste_hits,
                              'ep_envelope_hole_intersections': envelope_hits, 'paste_aperture_count': len(apertures)})
        ep_rows.append({'reference': ref, 'ep_pad_number': number, 'ep_copper_regions': len(eps),
                        'paste_aperture_count': len(apertures), 'paste_area_mm2': round(sum(q.Area() for q in apertures)/1e12,6),
                        'ep_envelope_mm': [to_mm(x0),to_mm(y0),to_mm(x1),to_mm(y1)],
                        'paste_hole_intersections': paste_hits, 'ep_envelope_hole_intersections': envelope_hits})
    checks['ep_paste_and_holes'] = result(ep_errors, finished_holes_checked=len(holes),
        method='Conservative 0.001 mm polygon approximation; complete drilled capsules/circles checked against paste and the entire EP bounding envelope.', components=ep_rows)

    # Check every actual via drill against all paste pads on both surfaces.
    # PTH/NPTH component holes are intentionally excluded from this global check.
    paste_errors=[];paste_shapes=[];nonzero_margins=[]
    for f in fps:
        for pad in f.Pads():
            for layer,copper_layer in [(p.F_Paste,p.F_Cu),(p.B_Paste,p.B_Cu)]:
                if not pad.IsOnLayer(layer):continue
                aperture=adjusted_paste_pad(pad,layer)
                if aperture is None:continue
                margin=pad.GetSolderPasteMargin(layer)
                detail={'reference':f.GetReference(),'pad':pad.GetNumber(),'layer':b.GetLayerName(layer),
                        'position_mm':xy(pad.GetPosition()),'effective_margin_mm':xy(margin),
                        'aperture_size_mm':xy(aperture.GetSize(layer))}
                if margin.x or margin.y:nonzero_margins.append(detail)
                paste_shapes.append((detail,copper_layer,aperture,aperture.GetEffectiveShape(layer)))
        for graphic in f.GraphicalItems():
            if graphic.GetLayer() in (p.F_Paste,p.B_Paste):
                paste_errors.append({'unsupported_nonpad_paste_graphic':f.GetReference(),'layer':b.GetLayerName(graphic.GetLayer())})
    for graphic in b.GetDrawings():
        if graphic.GetLayer() in (p.F_Paste,p.B_Paste):
            paste_errors.append({'unsupported_nonpad_paste_graphic':'board','layer':b.GetLayerName(graphic.GetLayer())})
    via_count=0
    for via in b.GetTracks():
        if not isinstance(via,p.PCB_VIA):continue
        via_count+=1
        for detail,copper_layer,aperture,shape in paste_shapes:
            if via.IsOnLayer(copper_layer) and shape.Collide(via.GetPosition(),round(via.GetDrill()/2)):
                paste_errors.append({'via_uuid':via.m_Uuid.AsString(),'via_net':via.GetNetname(),
                                     'via_position_mm':xy(via.GetPosition()),'via_drill_mm':to_mm(via.GetDrill()),
                                     'paste_aperture':detail})
    checks['all_via_drills_vs_paste'] = result(paste_errors,via_drills_checked=via_count,
        paste_apertures_checked=len(paste_shapes),nonzero_margin_apertures=nonzero_margins,
        method='Native effective-shape collision against via center plus drill radius; detached pad geometry first incorporates actual paste margins using KiCad plotting rules. All F/B paste pads checked; component PTH/NPTH drills excluded.',
        plotting_rule_reference='https://docs.kicad.org/doxygen/plot__board__layers_8cpp_source.html')

    # Inner planes: use the saved filled copper, never silently refill the board.
    inner_errors, plane_rows = [], []
    inner = (p.In1_Cu, p.In2_Cu)
    if b.GetCopperLayerCount()!=4:
        inner_errors.append({'expected_four_copper_layers_actual':b.GetCopperLayerCount()})
    inner_tracks = [t for t in b.GetTracks() if not isinstance(t,p.PCB_VIA) and t.GetLayer() not in (p.F_Cu,p.B_Cu)]
    for t in inner_tracks:
        inner_errors.append({'forbidden_inner_track': b.GetLayerName(t.GetLayer()), 'net': t.GetNetname(),
                             'start_mm': xy(t.GetStart()), 'end_mm': xy(t.GetEnd())})
    for layer in inner:
        zones = [z for z in b.Zones() if z.IsOnLayer(layer) and not z.GetIsRuleArea()]
        if len(zones) != 1: inner_errors.append({'layer': b.GetLayerName(layer), 'expected_one_ground_zone_actual': len(zones)})
        for z in zones:
            poly = z.GetFilledPolysList(layer)
            area = poly.Area()/1e12
            outline_area = z.Outline().Area()/1e12
            ratio = area/outline_area if outline_area else 0
            if z.GetNetname() != 'GND' or not z.IsFilled() or poly.OutlineCount() != 1 or ratio < .90:
                inner_errors.append({'layer': b.GetLayerName(layer), 'net': z.GetNetname(), 'filled': z.IsFilled(),
                                     'filled_outline_count': poly.OutlineCount(), 'coverage_ratio': ratio})
            plane_rows.append({'layer': b.GetLayerName(layer), 'net': z.GetNetname(), 'saved_fill_present': z.IsFilled(),
                               'filled_polygon_outlines': poly.OutlineCount(), 'filled_area_mm2': round(area,6),
                               'zone_outline_area_mm2': round(outline_area,6), 'filled_area_ratio': round(ratio,6)})
    checks['inner_ground_planes_and_routing_layers'] = result(inner_errors,
        acceptance='One saved connected filled GND polygon per inner layer, >=90% of its zone-outline area, no inner-layer tracks/arcs. Through vias are allowed.',
        inner_tracks_or_arcs=len(inner_tracks), planes=plane_rows,
        scope_limit='Polygon connectivity is not a minimum-neck-width or every-return-path proof.')

    # Official RP2350 Fig 24 requires L2 copper cleared beneath all LX copper.
    # Boolean intersection of actual saved copper, pads and tracks is stronger
    # than checking only the keepout bounds or its declared polygon.
    def layer_copper(layer, net_filter=None):
        copper = p.SHAPE_POLY_SET()
        def matches(item): return net_filter is None or item.GetNetname().rsplit('/',1)[-1] == net_filter
        for z in b.Zones():
            if z.IsOnLayer(layer) and not z.GetIsRuleArea() and matches(z):
                copper.BooleanAdd(z.GetFilledPolysList(layer))
        for f in fps:
            for pad in f.Pads():
                if pad.IsOnLayer(layer) and pad.GetAttribute()!=p.PAD_ATTRIB_NPTH and matches(pad):
                    poly=p.SHAPE_POLY_SET()
                    pad.TransformShapeToPolygon(poly,layer,0,mm(.001),p.ERROR_OUTSIDE)
                    copper.BooleanAdd(poly)
        for t in b.GetTracks():
            if t.IsOnLayer(layer) and matches(t):
                poly=p.SHAPE_POLY_SET()
                t.TransformShapeToPolygon(poly,layer,0,mm(.001),p.ERROR_OUTSIDE)
                copper.BooleanAdd(poly)
        return copper
    lx_copper=layer_copper(p.F_Cu,'VREG_LX')
    underneath=layer_copper(p.In1_Cu)
    underneath.BooleanIntersection(lx_copper)
    lx_area=lx_copper.Area()/1e12
    overlap_area=underneath.Area()/1e12
    lx_errors=[]
    if lx_area<=0:lx_errors.append({'missing_lx_copper':True})
    if overlap_area>.000001:lx_errors.append({'in1_copper_beneath_lx_mm2':round(overlap_area,9)})
    checks['rp_lx_adjacent_layer_clearance'] = result(lx_errors,
        lx_front_copper_area_mm2=round(lx_area,9), in1_copper_beneath_lx_mm2=round(overlap_area,9),
        intersection_area_tolerance_mm2=.000001,
        method='Boolean intersection of actual saved filled copper and track/via/pad geometry; conservative 0.001 mm polygon approximation. All In1 nets are considered.',
        reference='https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf#page=456',
        reference_section='6.3.8, printed page 455, Figure 24; immediately adjacent copper layer only.')

    # Verify the intended long, straight, mutually coupled USB trunk only.
    usb_errors, usb_rows = [], []
    y_start, y_end = 25.95, 40.048
    def find_pad(ref, number): return next(q for q in by_ref[ref].Pads() if q.GetNumber()==str(number))
    def intervals_cover(intervals, start, end):
        cursor=start
        for a,z in sorted(intervals):
            if a > cursor+.000003: return False
            cursor=max(cursor,z)
        return cursor >= end-.000003
    for ref, x_expected in [('R110',50.0),('R111',50.358)]:
        net = find_pad(ref,1).GetNetname()
        spans=[]
        for t in b.GetTracks():
            if isinstance(t,p.PCB_VIA) or isinstance(t,p.PCB_ARC) or t.GetNetname()!=net or t.GetLayer()!=p.F_Cu: continue
            a,z=xy(t.GetStart()),xy(t.GetEnd())
            if abs(a[0]-x_expected)>.000003 or abs(z[0]-x_expected)>.000003: continue
            lo=max(y_start,min(a[1],z[1])); hi=min(y_end,max(a[1],z[1]))
            if hi <= lo: continue
            spans.append([lo,hi])
            if abs(to_mm(t.GetWidth())-.158)>.000003:
                usb_errors.append({'net':net,'incorrect_trunk_width_mm':to_mm(t.GetWidth()),'span_y_mm':[lo,hi]})
        covered=intervals_cover(spans,y_start,y_end)
        if not covered: usb_errors.append({'net':net,'missing_straight_trunk_coverage':spans})
        usb_rows.append({'net':net,'x_mm':x_expected,'layer':'F.Cu','width_mm':.158,
                         'verified_spans_y_mm':spans,'complete_required_span':covered})
    ground_samples=[]
    for layer in inner:
        ground_zones=[z for z in b.Zones() if z.IsOnLayer(layer) and not z.GetIsRuleArea() and z.GetNetname()=='GND']
        # The complete rectangular projection includes both traces and their gap.
        projection=p.SHAPE_POLY_SET();projection.NewOutline()
        for xx,yy in [(49.921,y_start),(50.437,y_start),(50.437,y_end),(49.921,y_end)]:
            projection.Append(mm(xx),mm(yy))
        for z in ground_zones:projection.BooleanSubtract(z.GetFilledPolysList(layer))
        missing_area=projection.Area()/1e12
        if missing_area>.000001:
            usb_errors.append({'layer':b.GetLayerName(layer),'missing_ground_under_coupled_span_mm2':round(missing_area,9)})
        missing=[]; sample_count=0
        for step in range(143):
            yy=y_start+(y_end-y_start)*step/142
            for xx in [50.0,50.179,50.358]:
                sample_count+=1
                if not any(z.GetFilledPolysList(layer).Contains(vector((xx,yy))) for z in ground_zones):missing.append([round(xx,6),round(yy,6)])
        if missing:usb_errors.append({'layer':b.GetLayerName(layer),'missing_usb_ground_samples_mm':missing})
        ground_samples.append({'layer':b.GetLayerName(layer),'sample_count':sample_count,'missing_count':len(missing),
                               'missing_coupled_span_ground_area_mm2':round(missing_area,9)})
    checks['usb_straight_coupled_trunk'] = result(usb_errors, common_span_y_mm=[y_start,y_end],
        common_span_length_mm=round(y_end-y_start,6), nominal_center_spacing_mm=.358,
        nominal_copper_edge_gap_mm=.2, traces=usb_rows, ground_reference_samples=ground_samples,
        scope='Only the specified straight coupled span; escape widths/gaps/impedance are not generalized from this result.')

    # Measure source-side placement and copper length for all 36 link series resistors.
    series_errors, series_rows = [], []
    for index, letter in enumerate('ABC'):
        for signal in SIGNALS:
            net=letter+'_'+signal
            resistors=[c for c in components.values() if c['reference'].startswith('R') and c['value'].startswith('22R')
                       and {q.get('net') for q in c['pins'].values()} == {net,net+'_C5'}]
            if len(resistors)!=1:
                series_errors.append({'signal':net,'expected_one_22R_actual':len(resistors)});continue
            resistor=resistors[0]
            from_c5=signal.startswith('TX') or signal=='RX_CLK'
            source_ref='U'+str(201+index*100) if from_c5 else 'U101'
            source_net=net+'_C5' if from_c5 else net
            source_numbers=[num for num,pin in components[source_ref]['pins'].items() if pin.get('net')==source_net]
            series_numbers=[num for num,pin in resistor['pins'].items() if pin.get('net')==source_net]
            if len(source_numbers)!=1 or len(series_numbers)!=1:
                series_errors.append({'signal':net,'ambiguous_source_or_series_pad':True});continue
            source_pad=find_pad(source_ref,source_numbers[0]); series_pad=find_pad(resistor['reference'],series_numbers[0])
            aa,zz=xy(source_pad.GetPosition()),xy(series_pad.GetPosition())
            distance=math.dist(aa,zz)
            source_name=source_pad.GetNetname()
            traces=[t for t in b.GetTracks() if not isinstance(t,p.PCB_VIA) and t.GetNetname()==source_name]
            vias=[t for t in b.GetTracks() if isinstance(t,p.PCB_VIA) and t.GetNetname()==source_name]
            routed_length=sum(p.ToMM(t.GetLength()) for t in traces)
            if not traces:series_errors.append({'signal':net,'missing_source_to_series_tracks':source_name})
            series_rows.append({'signal':net,'clock_or_control':signal.endswith(('CLK','VALID')),
                'source_reference':source_ref,'source_pad':source_numbers[0],
                'series_reference':resistor['reference'],'series_source_pad':series_numbers[0],
                'source_xy_mm':aa,'series_source_pad_xy_mm':zz,'source_center_to_series_pad_mm':round(distance,6),
                'source_net':source_name,'source_net_total_trace_length_mm':round(routed_length,6),
                'source_net_via_count':len(vias),
                'placement_attention':distance>(3 if from_c5 else 10),
                'attention_threshold_mm':3 if from_c5 else 10})
    checks['source_series_placement'] = result(series_errors, expected_series_count=36, actual_series_count=len(series_rows),
        scope='Center-to-center Euclidean distance and total copper length on the source-side net, not a timing/SI certification. 3 mm C5 / 10 mm RP are review attention thresholds, not vendor limits.',
        max_c5_distance_mm=max((r['source_center_to_series_pad_mm'] for r in series_rows if r['source_reference']!='U101'),default=None),
        max_rp_distance_mm=max((r['source_center_to_series_pad_mm'] for r in series_rows if r['source_reference']=='U101'),default=None),
        attention_rows=[r['signal'] for r in series_rows if r['placement_attention']], signals=series_rows)

    # Build only in-memory connectivity, preserving the PCB bytes and saved fills.
    b.BuildConnectivity()
    unconnected=int(b.GetConnectivity().GetUnconnectedCount(False))
    checks['physical_connectivity'] = result([] if unconnected==0 else [{'unconnected_items':unconnected}],
        unconnected_items=unconnected,
        scope='KiCad connectivity count from the saved board; does not replace copper-short or full-rule DRC.')
    after_hashes={name:digest(path) for name,path in input_paths.items()}
    checks['input_files_unchanged'] = result([] if before_hashes==after_hashes else [{'before':before_hashes,'after':after_hashes}])
    report['automated_status']='fail' if any(c['status']=='fail' for c in checks.values()) else 'pass'
    report['release_status']='expert_and_manufacturing_validation_required'
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--board',type=Path,default=BASE/'FarmMesh-Node.kicad_pcb')
    parser.add_argument('--output',type=Path,default=BASE/'reports/pcb-verification.json')
    parser.add_argument('--share',type=Path,default=Path(os.environ.get('KICAD_SHARE',str(Path.home()/'Applications/KiCad/KiCad.app/Contents/SharedSupport'))))
    args=parser.parse_args()
    try:
        report=run(args.board,args.share)
    except Exception as error:
        report={'schema_version':1,'automated_status':'error','read_only':True,
                'error':type(error).__name__+': '+str(error),'board':str(args.board),
                'release_status':'verification_incomplete'}
        import traceback
        traceback.print_exc()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'automated_status':report['automated_status'],'report':str(args.output)}))
    return 0 if report['automated_status']=='pass' else 1


if __name__=='__main__':
    sys.exit(main())
