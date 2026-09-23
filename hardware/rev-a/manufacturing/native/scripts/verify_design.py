#!/usr/bin/env python3
"""Audit KiCad-exported connectivity and actual loaded footprint pad numbers.

Run with KiCad's Python (pcbnew required), after regenerating and exporting
reports/netlist.xml. This compares the parsed electrical result to the review
manifest; it is not an electrical simulation or a substitute for datasheets.
"""
import collections
import csv
import hashlib
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET
import pcbnew

BASE = Path(__file__).resolve().parents[1]
SHARE = Path(os.environ.get('KICAD_SHARE', str(Path.home() / 'Applications/KiCad/KiCad.app/Contents/SharedSupport')))
manifest = json.loads((BASE / 'design-manifest.json').read_text())
components = {m['reference']: m for m in manifest if not m['reference'].startswith('#')}
xml = ET.parse(BASE / 'reports/netlist.xml').getroot()
# The source path is metadata; keep the committed report machine-independent.
netlist_path = BASE / 'reports/netlist.xml'
netlist_path.write_text(netlist_path.read_text().replace(str(BASE) + '/', ''))
actual = {}
actual_groups = {}
for net in xml.findall('nets/net'):
    nodes = {(n.attrib['ref'], n.attrib['pin']) for n in net.findall('node') if n.attrib['ref'] in components}
    actual_groups[net.attrib['code']] = nodes
    for node in nodes:
        assert node not in actual, ('pin in two nets', node)
        actual[node] = net.attrib['code']

expected = collections.defaultdict(set)
for ref, m in components.items():
    for num, pin in m['pins'].items():
        n = pin['net']
        if n is None:
            continue
        global_ = n in {'GND', '+3V3', 'VBAT_PROTECTED', 'PWR_GOOD', 'BAT_SENSE', 'RP_USB_DM', 'RP_USB_DP', 'USB_VBUS_SENSE','CORE_1V1','RP_RUN'} or n.startswith(('A_', 'B_', 'C_')) and not n.endswith('_C5')
        key = ('global', n) if global_ else (m['sheet'], n)
        expected[key].add((ref, num))
for key, nodes in expected.items():
    ids = {actual.get(node) for node in nodes}
    assert None not in ids and len(ids) == 1, ('open or missing connection', key, nodes, ids)
    code = next(iter(ids))
    assert actual_groups[code] == nodes, ('unexpected short or missing expected node', key, nodes ^ actual_groups[code])

footprints = {}
for ref, m in components.items():
    fp = m['footprint']
    assert fp, ('unassigned footprint', ref)
    if fp not in footprints:
        lib, name = fp.split(':', 1)
        folder = BASE / 'FarmMesh.pretty' if lib == 'FarmMesh' else SHARE / 'footprints' / (lib + '.pretty')
        loaded = pcbnew.FootprintLoad(str(folder), name)
        assert loaded is not None, ('footprint does not load', fp)
        numbers = sorted({p.GetNumber() for p in loaded.Pads() if p.GetNumber()})
        footprints[fp] = {'pad_numbers': numbers, 'copper_pad_regions': len(list(loaded.Pads()))}
    actual_pads = set(footprints[fp]['pad_numbers'])
    expected_pads = set(m['pins'])
    assert actual_pads == expected_pads, ('symbol / footprint pad mismatch', ref, fp, expected_pads - actual_pads, actual_pads - expected_pads)

rows = collections.defaultdict(list)
for ref, m in components.items():
    rows[(m['value'], m['mpn'], m['footprint'])].append(ref)
with (BASE / 'BOM.csv').open('w', newline='') as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(['References', 'Quantity', 'Value', 'Manufacturer part number', 'Footprint', 'Selection status'])
    for (value, mpn, fp), refs in sorted(rows.items()):
        w.writerow([', '.join(sorted(refs)), len(refs), value, mpn, fp, 'PCB feature; do not assemble' if mpn in {'PCB-FEATURE','PCB_FEATURE_NOT_PURCHASED'} else 'Prototype selected; see parts-selection.json' if mpn else 'MPN TBD; footprint provisional'])

rp = components['U101']
by_name = {p['name']: num for num, p in rp['pins'].items()}
gpio_rows = []
signals = ['TX_D0', 'TX_D1', 'TX_D2', 'TX_D3', 'TX_CLK', 'TX_VALID', 'RX_D0', 'RX_D1', 'RX_D2', 'RX_D3', 'RX_CLK', 'RX_VALID']
c5_pads = [6, 7, 13, 14, 17, 16, 8, 10, 11, 12, 21, 23]
for i, letter in enumerate('ABC'):
    for j, (signal, pad) in enumerate(zip(signals, c5_pads)):
        rp_gpio = i * 12 + j
        module = components['U' + str(201 + i * 100)]
        gpio_rows.append([letter, signal, 'C5 -> RP' if signal.startswith('TX') or signal == 'RX_CLK' else 'RP -> C5', module['pins'][str(pad)]['name'], pad, rp_gpio, by_name['GPIO' + str(rp_gpio)], i, 16 if i == 2 else 0])
with (BASE / 'gpio-pinmap.csv').open('w', newline='') as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(['Link', 'Signal (C5 perspective)', 'Direction', 'C5 GPIO', 'C5 module pad', 'RP GPIO', 'RP package pad', 'Candidate PIO', 'PIO GPIOBASE'])
    w.writerows(gpio_rows)

report = {'status': 'pass', 'kicad_version': pcbnew.Version(), 'component_count': len(components), 'expected_connected_net_groups': len(expected), 'connected_pins_checked': sum(map(len, expected.values())), 'interface_signals': len(gpio_rows), 'footprints': footprints, 'limits': ['Connectivity and pad numbers only; no simulation, physical PCB, timing or RF validation.', 'Default KiCad ERC is a separate report; no ERC exclusions added.', 'BOM includes PCB features explicitly marked do not assemble; manufacturing/BOM-assembly.csv is the fitted-only export. Part selection and fabrication approval are separate gates.']}
artifacts = sorted(BASE.glob('*.kicad_sch')) + [BASE / 'design-manifest.json', netlist_path]
report['sha256'] = {str(p.relative_to(BASE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts}
(BASE / 'reports/connectivity-and-footprints.json').write_text(json.dumps(report, indent=2) + '\n')
print('PASS:', len(components), 'components;', len(expected), 'connected nets;', len(footprints), 'loaded footprint types;', len(gpio_rows), 'interface signals')
