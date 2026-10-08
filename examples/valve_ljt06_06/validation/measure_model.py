import json, sys, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'examples/elbow/elbow_clean_rebuild'))
import build_elbow_v10_spec as b
from sw_client import _get
s=b.TargetClient();s.connect(False,False);d=s._active_doc()
target=ROOT/'examples/valve_ljt06_06/output/valve_LJT06_06.SLDPRT'
assert Path(_get(d,'GetPathName')).resolve()==target.resolve()
out=ROOT/'examples/valve_ljt06_06/output/full_validation';out.mkdir(parents=True,exist_ok=True)
rows=[]
bodies=d.GetBodies2(0,False)
for body in bodies:
 for i,f in enumerate(_get(body,'GetFaces')):
  surf=_get(f,'GetSurface')
  row={'id':i,'box_mm':[v*1000 for v in _get(f,'GetBox')],'normal':list(_get(f,'Normal')),'area_mm2':_get(f,'GetArea')*1e6,'owner':_get(_get(f,'GetFeature'),'Name'),'surface_identity':_get(surf,'Identity'),'is_cone':bool(_get(surf,'IsCone'))}
  for typ,prop in [('plane','PlaneParams'),('cylinder','CylinderParams'),('torus','TorusParams')]:
   if _get(surf,{'plane':'IsPlane','cylinder':'IsCylinder','torus':'IsTorus'}[typ]):
    row['type']=typ;row['params_si']=list(_get(surf,prop));break
  edges=[]
  for e in _get(f,'GetEdges'):
   c=_get(e,'GetCurve');er={}
   for label,meth in [('start','GetStartVertex'),('end','GetEndVertex')]:
    v=_get(e,meth)
    er[label]=[x*1000 for x in _get(v,'GetPoint')] if v else None
   if _get(c,'IsCircle'):er['circle_si']=list(_get(c,'CircleParams'))
   er['line']=bool(_get(c,'IsLine'));edges.append(er)
  row['edges']=edges;rows.append(row)
features=[];seen=set()
def visit(f):
 name=_get(f,'Name');typ=_get(f,'GetTypeName2')
 if name in seen:return
 seen.add(name);row={'name':name,'type':typ}
 if typ in ['CosmeticThread','Fillet']:
  fd=_get(f,'GetDefinition')
  for key in (['Diameter','ThreadCallout','BlindDepth','EndCondition'] if typ=='CosmeticThread' else ['DefaultRadius']):
   try:row[key]=_get(fd,key)
   except Exception as ex:row[key]={'error':str(ex)}
 features.append(row)
 child=_get(f,'GetFirstSubFeature')
 while child:visit(child);child=_get(child,'GetNextSubFeature')
f=_get(d,'FirstFeature')
while f:visit(f);f=_get(f,'GetNextFeature')
(out/'features.json').write_text(json.dumps(features,ensure_ascii=False,indent=2),'utf-8')
report={'model_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'body_count':len(bodies),'faces':rows}
(out/'measurements.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'body_count':len(bodies),'faces':len(rows),'measurement_path':str(out/'measurements.json')}))

