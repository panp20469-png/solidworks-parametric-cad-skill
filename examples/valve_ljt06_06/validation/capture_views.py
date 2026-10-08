"""以实际相机矩阵及非破坏剖切记录证明视图，不保存显示状态到零件。"""
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import pythoncom
from win32com.client import VARIANT
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'examples/elbow/elbow_clean_rebuild'))
import build_elbow_v10_spec as b
from sw_client import _get, _invoke, _resolve_dispid, _plane_candidates
OUT=ROOT/'examples/valve_ljt06_06/output/full_validation'
OUT.mkdir(parents=True,exist_ok=True)
TARGET=OUT.parent/'valve_LJT06_06.SLDPRT'
sw=b.TargetClient();sw.connect(False,False)
doc=sw._active_doc()
assert Path(_get(doc,'GetPathName')).resolve()==TARGET.resolve()
before=hashlib.sha256(TARGET.read_bytes()).hexdigest()
rows=[]

def orientation(right,up,normal):
    arr=tuple(v for i in range(3) for v in (right[i],up[i],normal[i]))+(0,0,0,1,0,0,0)
    mu=_get(sw._app,'GetMathUtility')
    doc.ActiveView.Orientation3=_invoke(mu,_resolve_dispid(mu,'CreateTransform'),VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,arr))
    actual=list(_get(doc.ActiveView.Orientation3,'ArrayData'))
    assert max(abs(a-c) for a,c in zip(arr[:9],actual[:9]))<1e-8
    return actual

def capture(name,right,up,normal,section=None):
    sw.set_display_mode('shaded_with_edges' if name=='isometric' else 'hidden_lines_removed')
    matrix=orientation(right,up,normal)
    doc.ClearSelection2(True);_get(doc,'ViewZoomtofit2');_get(doc,'GraphicsRedraw2');time.sleep(.6)
    bmp=OUT/(name+'.bmp');png=OUT/(name+'.png')
    assert doc.SaveBMP(str(bmp),1400,1050)
    Image.open(bmp).save(png,format='PNG')
    rows.append({'name':name,'camera_matrix':matrix,'requested_normal':normal,'section':section,'path':png.name,'sha256':hashlib.sha256(png.read_bytes()).hexdigest()})

def section(plane,offset,reverse=False):
    mgr=doc.ModelViewManager
    data=_invoke(mgr,_resolve_dispid(mgr,'CreateSectionViewData'))
    f=None
    for candidate in _plane_candidates(plane):
        f=doc.FeatureByName(candidate)
        if f is not None:break
    assert f is not None,plane
    data.FirstPlane=f;data.FirstOffset=offset/1000
    data.FirstReverseDirection=reverse;data.FirstRotationX=0.;data.FirstRotationY=0.
    data.Redraw=True;data.ShowSectionCap=True;data.KeepCapColor=False;data.GraphicsOnlySection=True
    ok=_invoke(mgr,_resolve_dispid(mgr,'CreateSectionView'),data)
    assert ok
    return {'plane':_get(f,'Name'),'offset_mm':data.FirstOffset*1000,'reverse':bool(data.FirstReverseDirection),'created':bool(ok),'graphics_only':True,'plane_transform':list(_get(_get(_get(f,'GetSpecificFeature2'),'Transform'),'ArrayData'))}

# 普通视图在剖切前采集；脚本必须从未剖切的保存模型开始。
capture('front',(1,0,0),(0,0,1),(0,-1,0))
capture('top',(1,0,0),(0,1,0),(0,0,1))
capture('C',(-1,0,0),(0,0,1),(0,1,0))
capture('B_outer',(0,1,0),(0,0,1),(1,0,0))
capture('isometric',(1/math.sqrt(2),1/math.sqrt(2),0),(-1/math.sqrt(6),1/math.sqrt(6),2/math.sqrt(6)),(1/math.sqrt(3),-1/math.sqrt(3),1/math.sqrt(3)))
capture('A_A',(1,0,0),(0,0,1),(0,-1,0),section('Top Plane',0,True))
# 用重新打开本任务模型清除剖切状态，避免RemoveSectionView返回值与显示状态不一致。
sw.close_document(_get(doc,'GetTitle'));sw.target_title=None
opened=sw.open_document(str(TARGET),True);sw.activate_document(opened['title']);doc=sw._active_doc()
capture('B_B',(0,-1,0),(0,0,1),(-1,0,0),section('Right Plane',-50,True))
for name,plane,offset,reverse,right,up,normal in [
    ('C_local','Top Plane',39,True,(-1,0,0),(0,0,1),(0,1,0)),
    ('D_local','Top Plane',-39,False,(1,0,0),(0,0,1),(0,-1,0)),
    ('top_section','Front Plane',50,False,(1,0,0),(0,1,0),(0,0,1))]:
    sw.close_document(_get(doc,'GetTitle'));sw.target_title=None
    opened=sw.open_document(str(TARGET),True);sw.activate_document(opened['title']);doc=sw._active_doc()
    capture(name,right,up,normal,section(plane,offset,reverse))
sw.close_document(_get(doc,'GetTitle'));sw.target_title=None
opened=sw.open_document(str(TARGET),False);sw.activate_document(opened['title'])
assert hashlib.sha256(TARGET.read_bytes()).hexdigest()==before
assert len({r['sha256'] for r in rows})==len(rows)
(OUT/'views.json').write_text(json.dumps({'model_sha256':before,'model_unchanged':True,'views':rows},indent=2),'utf-8')
print(json.dumps({'views':len(rows),'model_unchanged':True}))
