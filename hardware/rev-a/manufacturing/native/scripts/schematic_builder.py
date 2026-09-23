#!/usr/bin/env python3
"""Small native KiCad writer used for the review draft (requires sexpdata).

The generated schematics remain editable in KiCad. Regeneration overwrites them;
preserve manual edits before running build_design.py again.
"""
from __future__ import annotations
import copy, json, math, os, uuid
from pathlib import Path
import sexpdata as sx

S = sx.Symbol
BASE = Path(__file__).resolve().parents[1]
PROJECT = "FarmMesh-Node"
KICAD = Path(os.environ.get("KICAD_SHARE", str(Path.home() / "Applications/KiCad/KiCad.app/Contents/SharedSupport")))
ROOT_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, "farmmesh-rev-a/root"))

def uid(key): return str(uuid.uuid5(uuid.NAMESPACE_URL, "farmmesh-rev-a/" + key))
def e(tag, *args): return [S(tag), *args]
def val(node, key, default=None):
    for x in node:
        if isinstance(x, list) and x and str(x[0]) == key: return x[1]
    return default
def child(node, key):
    return next((x for x in node if isinstance(x, list) and x and str(x[0]) == key), None)
def effects(size=1.0, justify=None, hide=False):
    a=e('effects', e('font',e('size',size,size)))
    if justify: a.append(e('justify', *[S(v) for v in justify.split()]))
    if hide: a.append(e('hide',S('yes')))
    return a
def prop(k,v,x,y,hide=False,size=1.0,justify=None,angle=0):
    return e('property',k,str(v),e('at',x,y,angle),effects(size,justify,hide))
def dump(path, data):
    # Keep top-level forms on separate lines for review; KiCad can normalize later.
    path.write_text('('+str(data[0])+'\n'+'\n'.join('  '+sx.dumps(v) for v in data[1:])+'\n)\n')

LIBS={}; CUSTOM={}; MANIFEST=[]
PARTS = json.loads((BASE/'parts-selection.json').read_text()).get('by_reference', {}) if (BASE/'parts-selection.json').exists() else {}
def library_symbol(lib_id):
    lib,name=lib_id.split(':',1)
    if lib=='FarmMesh': return copy.deepcopy(CUSTOM[name])
    if lib not in LIBS:
        raw=sx.loads((KICAD/'symbols'/f'{lib}.kicad_sym').read_text())
        LIBS[lib]={x[1]:x for x in raw if isinstance(x,list) and x and str(x[0])=='symbol'}
    item=copy.deepcopy(LIBS[lib][name])
    parent=val(item,'extends')
    if parent:
        p=library_symbol(f'{lib}:{parent}')
        overrides={x[1] for x in item if isinstance(x,list) and str(x[0])=='property'}
        p=[x for x in p if not(isinstance(x,list) and str(x[0])=='property' and x[1] in overrides)]
        for x in p:
            if isinstance(x,list) and str(x[0])=='symbol': x[1]=x[1].replace(parent+'_',name+'_',1)
        p[1]=name
        p.extend(x for x in item[2:] if not(isinstance(x,list) and str(x[0])=='extends'))
        item=p
    return item

def pins_of(symbol):
    pins=[]
    for a in symbol:
        if isinstance(a,list) and a and str(a[0])=='symbol':
            for p in a:
                if isinstance(p,list) and p and str(p[0])=='pin':
                    pins.append(dict(number=str(val(p,'number')),name=val(p,'name'),kind=str(p[1]),at=child(p,'at')[1:]))
    return pins

def custom_ic(name, pin_specs, footprint, datasheet, width=25.4, height=50.8):
    # specs: number,name,type,x,y,angle (library coordinates, y up)
    a=e('symbol',name,e('pin_names',e('offset',0.8)),e('in_bom',S('yes')),e('on_board',S('yes')),
        prop('Reference','U',0,height/2+5.08),prop('Value',name,0,height/2+2.54),
        prop('Footprint',footprint,0,0,True),prop('Datasheet',datasheet,0,0,True))
    a.append(e('symbol',name+'_0_1',e('rectangle',e('start',-width/2,height/2),e('end',width/2,-height/2),e('stroke',e('width',0.254),e('type',S('default'))),e('fill',e('type',S('background'))))))
    body=e('symbol',name+'_1_1')
    for number,pname,kind,x,y,angle in pin_specs:
        body.append(e('pin',S(kind),S('line'),e('at',x,y,angle),e('length',5.08),e('name',pname,effects(1.0)),e('number',str(number),effects(1.0))))
    a.append(body);CUSTOM[name]=a
    return 'FarmMesh:'+name

class Sheet:
    def __init__(self, name, title, page):
        self.name=name; self.title=title; self.page=page
        self.id=ROOT_ID if page==1 else uid('file/'+name)
        self.block_id=uid('sheet/'+name)
        self.path='/'+ROOT_ID if page==1 else '/'+ROOT_ID+'/'+self.block_id
        self.items=[]; self.lib={}; self.refs={}; self.serial=0
    def new_id(self,kind):
        self.serial+=1;return uid(f'{self.name}/{kind}/{self.serial}')
    def text(self,text,x,y,size=1.4,bold=False):
        ef=effects(size,'left top')
        if bold: child(ef,'font').append(e('bold',S('yes')))
        self.items.append(e('text',text,e('at',x,y,0),ef,e('uuid',self.new_id('text'))))
    def wire(self,a,b):
        if a==b:return
        self.items.append(e('wire',e('pts',e('xy',*a),e('xy',*b)),e('stroke',e('width',0),e('type',S('default'))),e('uuid',self.new_id('wire'))))
    def label(self,net,x,y,angle=0,global_=True):
        if global_:
            self.items.append(e('global_label',net,e('shape',S('bidirectional')),e('at',x,y,angle),effects(0.95,'left' if angle in [0,90] else 'right'),e('uuid',self.new_id('label')),
                prop('Intersheetrefs','${INTERSHEET_REFS}',x,y,True,0.8)))
        else:self.items.append(e('label',net,e('at',x,y,angle),effects(0.95,'right bottom' if angle in [180,270] else 'left bottom'),e('uuid',self.new_id('label'))))
    def component(self, lib_id, ref, value, x,y,nets=None, rotation=0, footprint=None, mpn=None, fields=None, label_stub=5.08):
        selected=PARTS.get(ref,{})
        footprint=selected.get('footprint',footprint)
        mpn=selected.get('mpn',mpn)
        value=selected.get('value',value)
        sym=library_symbol(lib_id); defs=pins_of(sym)
        cached=copy.deepcopy(sym);cached[1]=lib_id;self.lib[lib_id]=cached
        props={a[1]:a[2] for a in sym if isinstance(a,list) and str(a[0])=='property'}
        fp=footprint if footprint is not None else props.get('Footprint','')
        pid=uid('component/'+ref)
        c=e('symbol',e('lib_id',lib_id),e('at',x,y,rotation),e('unit',1),e('in_bom',S('no' if ref.startswith(('#','TP','H')) else 'yes')),e('on_board',S('no' if ref.startswith('#') else 'yes')),e('dnp',S('no')),e('uuid',pid))
        ispassive=len(defs)<=2 and lib_id.startswith(('Device:','Switch:'))
        if fields:rx,ry,vx,vy=fields
        elif ispassive and (defs[0]['at'][1]!=defs[1]['at'][1]) == (rotation==0):rx,ry,vx,vy=x+3.0,y-1.2,x+3.0,y+1.2
        elif ispassive:rx,ry,vx,vy=x-3,y-5.0,x-3,y-2.5
        else:
            top=min([y-p['at'][1] for p in defs],default=y)-12.7
            rx,ry,vx,vy=x-5,top,x-5,top+2.54
        c.extend([prop('Reference',ref,rx,ry,ref.startswith('#'),1.1,'left',rotation%180),prop('Value',value,vx,vy,ref.startswith('#'),1.0,'left',rotation%180),prop('Footprint',fp,x,y,True),prop('Datasheet',props.get('Datasheet',''),x,y,True)])
        if mpn:c.append(prop('MPN',mpn,x,y,True))
        c.append(e('instances',e('project',PROJECT,e('path',self.path,e('reference',ref),e('unit',1)))))
        locations={};r=math.radians(rotation)
        for p in defs:
            px,py,pa=p['at']; dx=px*math.cos(r)-py*math.sin(r);dy=px*math.sin(r)+py*math.cos(r)
            locations[p['number']]=(round(x+dx,4),round(y-dy,4),(pa+rotation)%360)
            c.append(e('pin',p['number'],e('uuid',uid('pin/'+ref+'/'+p['number']))))
        self.items.append(c);self.refs[ref]=locations
        connected=set();usedcoords={};nets=nets or {}
        for p in defs:
            num=p['number']; net=nets.get(num,nets.get(p['name']))
            px,py,angle=locations[num]
            if net is not None:
                connected.add(num)
                coord=(px,py)
                if coord in usedcoords:
                    assert usedcoords[coord]==net,(ref,num,'stacked conflict');continue
                usedcoords[coord]=net
                d={0:(-label_stub,0),180:(label_stub,0),90:(0,label_stub),270:(0,-label_stub)}[angle]
                end=(round(px+d[0],4),round(py+d[1],4))
                self.wire((px,py),end)
                # Labels point away from their pin. Vertical labels use smaller text.
                la=(angle+180)%360
                across = net in {'GND','+3V3','VBAT_PROTECTED','PWR_GOOD','BAT_SENSE','RP_USB_DM','RP_USB_DP','USB_VBUS_SENSE','CORE_1V1','RP_RUN'} or net.startswith(('A_','B_','C_')) and not net.endswith('_C5')
                self.label(net,*end,angle=la,global_=across)
            else:
                if (px,py) not in usedcoords:
                    self.items.append(e('no_connect',e('at',px,py),e('uuid',self.new_id('nc'))));usedcoords[(px,py)]=None
        MANIFEST.append(dict(reference=ref,value=value,lib_id=lib_id,footprint=fp,mpn=mpn or "",sheet=self.name,
            pins={p['number']:dict(name=p['name'],type=p['kind'],net=nets.get(p['number'],nets.get(p['name']))) for p in defs}))
        return locations
    def subsheet(self,sheet,x,y,w=90,h=25):
        self.items.append(e('sheet',e('at',x,y),e('size',w,h),e('stroke',e('width',0.254),e('type',S('default'))),e('fill',e('color',0,0,0,0)),e('uuid',sheet.block_id),
            prop('Sheetname',sheet.title,x,y-2.54,False,1.3,'left'),prop('Sheetfile',sheet.name+'.kicad_sch',x,y+h+2.54,False,1,'left'),
            e('instances',e('project',PROJECT,e('path','/'+ROOT_ID,e('page',str(sheet.page)))))))
    def save(self):
        head=e('kicad_sch',e('version',20250114),e('generator',S('eeschema')),e('generator_version','10.0'),e('uuid',self.id),e('paper','A3'),
          e('title_block',e('title',self.title),e('date','2026-09-23'),e('rev','A1'),e('company','FarmMesh Node'),e('comment',1,'Prototype engineering - release status in RELEASE.md'),e('comment',2,'1S Li-ion battery input; no on-board charger')),
          e('lib_symbols',*self.lib.values()))
        head.extend(self.items)
        if self.page==1:head.append(e('sheet_instances',e('path','/',e('page','1'))))
        dump(BASE/(self.name+'.kicad_sch'),head)

def save_library():
    dump(BASE/'FarmMesh.kicad_sym',e('kicad_symbol_lib',e('version',20241209),e('generator',S('kicad_symbol_editor')),*CUSTOM.values()))
    sym_entries=[e('lib',e('name',n),e('type','KiCad'),e('uri','${KICAD10_SYMBOL_DIR}/'+n+'.kicad_sym'),e('options',''),e('descr','KiCad standard library')) for n in sorted(LIBS)]
    fp_names=sorted({m['footprint'].split(':')[0] for m in MANIFEST if m['footprint'] and not m['footprint'].startswith('FarmMesh:')})
    fp_entries=[e('lib',e('name',n),e('type','KiCad'),e('uri','${KICAD10_FOOTPRINT_DIR}/'+n+'.pretty'),e('options',''),e('descr','KiCad standard library')) for n in fp_names]
    dump(BASE/'sym-lib-table',e('sym_lib_table',e('version',7),e('lib',e('name','FarmMesh'),e('type','KiCad'),e('uri','${KIPRJMOD}/FarmMesh.kicad_sym'),e('options',''),e('descr','Project-specific reviewed draft symbols')),*sym_entries))
    dump(BASE/'fp-lib-table',e('fp_lib_table',e('version',7),e('lib',e('name','FarmMesh'),e('type','KiCad'),e('uri','${KIPRJMOD}/FarmMesh.pretty'),e('options',''),e('descr','Project-specific module land pattern')),*fp_entries))
    (BASE/'design-manifest.json').write_text(json.dumps(MANIFEST,indent=2)+'\n')

RFP='Resistor_SMD:R_0603_1608Metric'
CFP='Capacitor_SMD:C_0603_1608Metric'
def resistor(s,ref,value,x,y,a,b,rotation=90,mpn=None):
    return s.component('Device:R',ref,value,x,y,{'1':a,'2':b},rotation,RFP,mpn)
def capacitor(s,ref,value,x,y,rail,gnd='GND',footprint=CFP,mpn=None,label_stub=5.08):
    symbol='Device:C_Polarized' if 'CP_Elec' in footprint else 'Device:C'
    return s.component(symbol,ref,value,x,y,{'1':rail,'2':gnd},0,footprint,mpn,label_stub=label_stub)
