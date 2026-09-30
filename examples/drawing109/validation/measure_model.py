import json, sys, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'examples/elbow/elbow_clean_rebuild'))
import build_elbow_v10_spec as b
from sw_client import _get
s=b.TargetClient();s.connect(False,False);d=s._active_doc()
target=ROOT/'docs/demo/drawing109/drawing109.SLDPRT'
assert Path(_get(d,'GetPathName')).resolve()==target.resolve()
out=ROOT/'docs/demo/drawing109/full-validation';out.mkdir(exist_ok=True)
rows=[]
bodies=d.GetBodies2(0,False)
for body in bodies:
 for i,f in enumerate(_get(body,'GetFaces')):
  surf=_get(f,'GetSurface')
  row={'id':i,'box_mm':[v*1000 for v in _get(f,'GetBox')],'normal':list(_get(f,'Normal')),'area_mm2':_get(f,'GetArea')*1e6}
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
report={'model_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'body_count':len(bodies),'faces':rows}
(out/'measurements.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'body_count':len(bodies),'faces':len(rows),'measurement_path':str(out/'measurements.json')}))
