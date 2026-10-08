"""直接读取实体故障和特征错误；接口失败不能当作零错误。"""
import hashlib,json,sys
from pathlib import Path
import pythoncom
from win32com.client import VARIANT
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'examples/elbow/elbow_clean_rebuild'))
import build_elbow_v10_spec as b
from sw_client import _get,_invoke,_resolve_dispid
case=ROOT/'examples/valve_ljt06_06';out=case/'output/full_validation'
s=b.TargetClient();s.connect(False,False);doc=s._active_doc()
target=case/'output/valve_LJT06_06.SLDPRT'
assert Path(_get(doc,'GetPathName')).resolve()==target.resolve()
bodies=doc.GetBodies2(0,False);faults=[]
for body in bodies:
    fault=_get(body,'Check3')
    faults.append(0 if fault is None else int(_get(fault,'Count')))
features=[];seen=set()
def visit(f):
    name=_get(f,'Name')
    if name in seen:return
    seen.add(name)
    warning=VARIANT(pythoncom.VT_BYREF|pythoncom.VT_BOOL,False)
    code=_invoke(f,_resolve_dispid(f,'GetErrorCode2'),warning)
    features.append({'name':name,'type':_get(f,'GetTypeName2'),'code':code,'warning':bool(warning.value) if code else False})
    child=_get(f,'GetFirstSubFeature')
    while child:visit(child);child=_get(child,'GetNextSubFeature')
f=_get(doc,'FirstFeature')
while f:visit(f);f=_get(f,'GetNextFeature')
report={'model_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'body_count':len(bodies),'body_check3_fault_counts':faults,'features':features,'feature_errors':sum(bool(f['code']) and not f['warning'] for f in features),'feature_warnings':sum(bool(f['code']) and f['warning'] for f in features),'sources':['https://help.solidworks.com/2011/English/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IBody2~Check3.html','https://help.solidworks.com/2024/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IFeature~GetErrorCode2.html']}
(out/'native-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('features','sources')},ensure_ascii=True))
assert len(bodies)==1 and not sum(faults) and not report['feature_errors'] and not report['feature_warnings']
