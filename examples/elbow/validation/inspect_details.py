import sys,json,time,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/demo/elbow-validation'
sys.path.insert(0,str(ROOT/'examples/elbow/elbow_clean_rebuild'))
import build_elbow_v10_spec as b
from sw_client import _get
s=b.TargetClient();s.connect(False,False);d=s._active_doc()
assert Path(_get(d,'GetPathName')).resolve()==(ROOT/'docs/demo/elbow.SLDPRT').resolve()
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
(OUT/'features.json').write_text(json.dumps(features,ensure_ascii=False,indent=2),'utf-8')
print('FEATURES='+str(len(features)),flush=True)
faces=list(_get(d.GetBodies2(0,False)[0],'GetFaces'));views=[]
for name,index,axis in [('B',21,[-2**-.5,2**-.5,0]),('C',47,[3**.5/2,.5,0])]:
 d.ClearSelection2(True);assert faces[index].Select4(False,_get(d.SelectionManager,'CreateSelectData'))
 ok=d.Extension.RunCommand(169,'');time.sleep(.5)
 matrix=list(_get(_get(d.ActiveView,'Orientation3'),'ArrayData'))
 # 视线方向是旋转矩阵第三列；允许法向反向，图像另做外端面方向复核。
 normal=[matrix[2],matrix[5],matrix[8]]
 alignment=abs(sum(a*c for a,c in zip(normal,axis)))
 assert alignment>1-1e-6,(name,matrix,alignment)
 d.ClearSelection2(True);_get(d,'ViewZoomtofit2');_get(d,'GraphicsRedraw2')
 s.capture_screenshot(str(OUT/(name+'.bmp')))
 views.append({'name':name,'face':index,'requested_normal':axis,'normal_to_result':ok,'matrix':matrix,'normal_alignment':alignment})
(OUT/'end-view-log.json').write_text(json.dumps(views,indent=2),'utf-8')
print(json.dumps({'views':len(views)}))
