#!/usr/bin/env python3
"""Restore explicitly reviewed seed copper after a Specctra SES import.

KiCad's SES import replaces the board tracks/vias; routers may omit fixed
seed wiring from their session file. This tool merges exact seed geometry
without borrowing a NETINFO_ITEM from another BOARD. Default is read-only;
--write creates a backup and atomically replaces only the named trial board.
Run using KiCad's bundled Python, then refill zones and run full project DRC.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import shutil

import pcbnew as p
import wx


def point(v):
    return (int(v.x), int(v.y))


def copper_key(t):
    """Exact integer geometry, net name, and layer; endpoint order is immaterial."""
    if isinstance(t, p.PCB_VIA):
        layers = tuple(int(x) for x in t.GetLayerSet().Seq() if t.IsOnLayer(x))
        return ('via', t.GetNetname(), point(t.GetPosition()),
                tuple((x, t.GetWidth(x)) for x in layers), t.GetDrillValue(),
                t.TopLayer(), t.BottomLayer(), t.GetViaType())
    if isinstance(t, p.PCB_ARC):
        return ('arc', t.GetNetname(),
                tuple(sorted((point(t.GetStart()), point(t.GetEnd())))),
                point(t.GetMid()), t.GetWidth(), t.GetLayer())
    return ('track', t.GetNetname(),
            tuple(sorted((point(t.GetStart()), point(t.GetEnd())))),
            t.GetWidth(), t.GetLayer())


def footprint_geometry(b, position_quantum_nm=1):
    def pos(v):
        return tuple(round(x / position_quantum_nm) * position_quantum_nm for x in point(v))
    result = {}
    for f in b.GetFootprints():
        pads = []
        for pad in f.Pads():
            pads.append((pad.GetNumber(), pos(pad.GetPosition()),
                         point(pad.GetSize()), point(pad.GetDrillSize()),
                         pad.GetOrientationDegrees(), pad.GetShape(),
                         tuple(pad.GetLayerSet().Seq()), pad.GetNetname()))
        result[f.GetReference()] = (pos(f.GetPosition()),
            f.GetOrientationDegrees(), f.GetLayer(),
            (str(f.GetFPID().GetLibNickname()), str(f.GetFPID().GetLibItemName())),
            tuple(sorted(pads)))
    return result


def zone_geometry(b):
    result = []
    for z in b.Zones():
        poly = z.Outline()
        contours = []
        for i in range(poly.OutlineCount()):
            chain = poly.Outline(i)
            outer = tuple(point(chain.CPoint(j)) for j in range(chain.PointCount()))
            holes = []
            for h in range(poly.HoleCount(i)):
                chain = poly.Hole(i, h)
                holes.append(tuple(point(chain.CPoint(j)) for j in range(chain.PointCount())))
            contours.append((outer, tuple(holes)))
        result.append((z.GetNetname(), tuple(z.GetLayerSet().Seq()),
                       z.GetIsRuleArea(), tuple(contours)))
    return sorted(result)


def paste_hole_candidates(b, tracks):
    """Conservative circle/axis-aligned paste-pad box screening.

    A zero result proves no hole/paste-pad intersection. Positive results must
    be inspected against rounded/custom pad geometry; no false-safe claim is
    made for that case. Copper annulus overlap alone is not a drilled paste hole.
    """
    paste = []
    for f in b.GetFootprints():
        for pad in f.Pads():
            if not pad.IsOnLayer(p.F_Paste):
                continue
            # GetBoundingBox(F_Paste) includes the layer's effective pad shape.
            box = pad.GetBoundingBox(p.F_Paste)
            if box.GetWidth() <= 0 or box.GetHeight() <= 0:
                continue
            paste.append((f.GetReference(), pad.GetNumber(), box))
    hits = []
    for t in tracks:
        if not isinstance(t, p.PCB_VIA):
            continue
        x, y = point(t.GetPosition())
        radius = t.GetDrillValue() / 2
        for ref, padnum, box in paste:
            dx = max(box.GetLeft() - x, 0, x - box.GetRight())
            dy = max(box.GetTop() - y, 0, y - box.GetBottom())
            if math.hypot(dx, dy) < radius:
                hits.append({'ref': ref, 'pad': padnum,
                             'via_mm': [p.ToMM(x), p.ToMM(y)],
                             'drill_mm': p.ToMM(t.GetDrillValue()),
                             'net': t.GetNetname()})
    return hits


def merge(seed_path, trial_path, write=False):
    seed_path, trial_path = Path(seed_path).resolve(), Path(trial_path).resolve()
    if seed_path == trial_path:
        raise ValueError('Seed and trial must be different files')
    seed, trial = p.LoadBoard(str(seed_path)), p.LoadBoard(str(trial_path))
    seed_items = {copper_key(t): t for t in seed.GetTracks()}
    trial_items = {copper_key(t): t for t in trial.GetTracks()}
    sf, tf = footprint_geometry(seed), footprint_geometry(trial)
    changed_fps = sorted(ref for ref in set(sf) | set(tf) if sf.get(ref) != tf.get(ref))
    zones_match = zone_geometry(seed) == zone_geometry(trial)
    # SES can round coordinates ending in ...999 nm to the next micrometre;
    # retain the exact differences in the report while accepting a 10 nm grid.
    same_placement = footprint_geometry(seed, 10) == footprint_geometry(trial, 10)
    if not same_placement or not zones_match:
        raise RuntimeError(f'Trial changed seed geometry: footprints={changed_fps}, zones_match={zones_match}')
    missing = seed_items.keys() - trial_items.keys()
    new_items = [t for k, t in trial_items.items() if k not in seed_items]
    report = {'seed': str(seed_path), 'trial': str(trial_path),
              'seed_sha256': hashlib.sha256(seed_path.read_bytes()).hexdigest(),
              'trial_before_sha256': hashlib.sha256(trial_path.read_bytes()).hexdigest(),
              'seed_objects': len(seed.GetTracks()), 'seed_unique': len(seed_items),
              'trial_objects_before': len(trial.GetTracks()),
              'seed_retained_before': len(seed_items.keys() & trial_items.keys()),
              'seed_missing_before': len(missing), 'footprints_equal_on_10nm_grid': True,
              'footprints_with_sub_10nm_coordinate_rounding': changed_fps,
              'zone_outlines_equal': True,
              'new_via_count': sum(isinstance(t, p.PCB_VIA) for t in new_items),
              'new_via_paste_hole_candidates': paste_hole_candidates(trial, new_items)}
    if write and missing:
        backup = trial_path.with_suffix('.pre-seed-merge.kicad_pcb')
        if backup.exists():
            raise FileExistsError(f'Refusing to overwrite backup: {backup}')
        nets = {n.GetNetname(): n.GetNetCode() for n in trial.GetNetsByNetcode().values()}
        unknown = sorted({seed_items[k].GetNetname() for k in missing} - set(nets))
        if unknown:
            raise RuntimeError(f'Trial is missing seed nets: {unknown}')
        for key in sorted(missing, key=repr):
            source = seed_items[key]
            clone = source.Duplicate()
            clone.SetParent(trial)
            # Resolve within the destination BOARD; never copy a source net object.
            clone.SetNetCode(nets[source.GetNetname()])
            trial.Add(clone)
        trial.BuildConnectivity()
        final = {copper_key(t) for t in trial.GetTracks()}
        if not set(seed_items).issubset(final):
            raise RuntimeError('Post-merge seed copper preservation failed')
        if footprint_geometry(trial) != tf or zone_geometry(trial) != zone_geometry(seed):
            raise RuntimeError('Post-merge non-routing geometry unexpectedly changed')
        temp = trial_path.with_suffix('.seed-merge-tmp.kicad_pcb')
        p.SaveBoard(str(temp), trial)
        reloaded = p.LoadBoard(str(temp))
        if not set(seed_items).issubset({copper_key(t) for t in reloaded.GetTracks()}):
            temp.unlink()
            raise RuntimeError('Serialized seed copper preservation failed')
        shutil.copy2(trial_path, backup)
        temp.replace(trial_path)
        report['backup'] = str(backup)
    report['written'] = bool(write and missing)
    report['trial_objects_after'] = len(trial.GetTracks())
    report['restored_unique'] = len(missing) if write else 0
    report['trial_after_sha256'] = hashlib.sha256(trial_path.read_bytes()).hexdigest()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('seed')
    parser.add_argument('trials', nargs='+')
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--report')
    args = parser.parse_args()
    app = wx.App(False)
    quiet = wx.LogNull()
    result = [merge(args.seed, path, args.write) for path in args.trials]
    data = json.dumps(result, indent=2)
    if args.report:
        Path(args.report).write_text(data + '\n')
    print(data)


if __name__ == '__main__':
    main()
