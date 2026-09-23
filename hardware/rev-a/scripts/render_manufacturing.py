#!/usr/bin/env python3
"""Render actual Gerber/Excellon bytes for independent visual review.

Requires gerbonara 1.6.3 and PyMuPDF. Outputs are review evidence outside the
sealed manufacturing tree. This does not approve or modify manufacturing data.
"""
from pathlib import Path
import argparse,hashlib,json
import gerbonara
from gerbonara import GerberFile, ExcellonFile, LayerStack
import pymupdf as fitz

BASE=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    q=argparse.ArgumentParser(description=__doc__)
    q.add_argument('--input',type=Path,default=BASE/'manufacturing')
    q.add_argument('--output',type=Path,default=BASE/'review/gerber')
    a=q.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    files=sorted((a.input/'gerber').glob('*.gbr'));drills=sorted((a.input/'drill').glob('*.drl'))
    assert len(files)==11 and len(drills)==2
    layers={p.stem.split('FarmMesh-Node-',1)[-1]:GerberFile.open(p)for p in files}
    edge=layers['Edge_Cuts'];bounds=edge.bounding_box()
    pth=ExcellonFile.open(next(p for p in drills if p.name.endswith('-PTH.drl')))
    npth=ExcellonFile.open(next(p for p in drills if p.name.endswith('-NPTH.drl')))
    def save(name,svg):
        path=a.output/(name+'.svg');path.write_text(str(svg))
        doc=fitz.open(path);pdf=fitz.open('pdf',doc.convert_to_pdf())
        pdf[0].get_pixmap(matrix=fitz.Matrix(4,4),alpha=False).save(a.output/(name+'.png'))
    for name,g in layers.items():save(name,g.to_svg(force_bounds=bounds,margin=1))
    combined=LayerStack({('top','paste'):layers['F_Paste'],('mechanical','outline'):edge},drill_pth=pth,drill_npth=npth)
    save('paste-drill-overlay',combined.to_svg(force_bounds=bounds,margin=1,colors={'top paste':'#333333','mechanical outline':'#777777','drill pth':'#e00000','drill npth':'#0066cc'}))
    report={'status':'rendered_requires_human_or_agent_visual_inspection','renderer':'gerbonara '+gerbonara.__version__+' / PyMuPDF '+fitz.VersionBind,
            'source_sha256':{str(p.relative_to(a.input)):sha(p)for p in files+drills},
            'outline_bounds_mm':bounds,'gerber_layer_count':len(files),'pth_drill_objects':len(pth.objects),'npth_drill_objects':len(npth.objects),
            'rendered_files':{p.name:sha(p)for p in sorted(a.output.glob('*'))if p.suffix in ['.svg','.png']}}
    (a.output/'render-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k not in ['source_sha256','rendered_files']}))
if __name__=='__main__':main()
