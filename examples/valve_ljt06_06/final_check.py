"""独立读取最终尺寸外包络，并保存Z轴朝上的观察视图。"""
import hashlib
import json
import math
from pathlib import Path
import sys
import pythoncom
from win32com.client import VARIANT

HERE=Path(__file__).resolve().parent
OUT=HERE/'output'
sys.path.insert(0,str(HERE.parent/'elbow/elbow_clean_rebuild'))
import build_elbow_v10_spec as b
from sw_client import _get, _invoke, _resolve_dispid

def finish(sw):
    c=json.loads((HERE/'contract.json').read_text('utf-8'))
    p=c['dimensions']
    target=OUT/'valve_LJT06_06.SLDPRT'
    doc=sw._active_doc()
    assert Path(_get(doc,'GetPathName')).resolve()==target.resolve()
    body=doc.GetBodies2(0,False)[0]
    extrema=[]
    for direction in [(-1,0,0),(0,-1,0),(0,0,-1),(1,0,0),(0,1,0),(0,0,1)]:
        vals=[VARIANT(pythoncom.VT_BYREF|pythoncom.VT_R8,0.0) for _ in range(3)]
        ok=_invoke(body,_resolve_dispid(body,'GetExtremePoint'),*direction,*vals)
        if not ok: raise RuntimeError('Extreme point query failed')
        pt=[v.value*1000 for v in vals]
        extrema.append(pt[next(i for i,v in enumerate(direction) if v)])
    expected=[-p['port_axis_offset']-p['c_hole_pitch']/2-p['ear_radius'],-p['port_half_length'],0,p['base_width']/2,p['port_half_length'],p['total_height']]
    if max(abs(x-y) for x,y in zip(extrema,expected))>0.01:
        raise RuntimeError(f'Envelope mismatch: actual={extrema}, expected={expected}')
    root2=math.sqrt(2); root3=math.sqrt(3); root6=math.sqrt(6)
    arr=(1/root2,-1/root6,1/root3,1/root2,1/root6,-1/root3,0,2/root6,1/root3,0,0,0,1,0,0,0)
    mu=_get(sw._app,'GetMathUtility')
    transform=_invoke(mu,_resolve_dispid(mu,'CreateTransform'),VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,arr))
    doc.ActiveView.Orientation3=transform
    doc.ClearSelection2(True)
    _get(doc,'ViewZoomtofit2'); _get(doc,'GraphicsRedraw2')
    doc.SaveBMP(str(OUT/'valve_isometric.bmp'),1400,1050)
    sw.save_document(str(target))
    report={'status':'BASIC_CHECK_PASS','envelope_actual_mm':extrema,'envelope_expected_mm':expected,'overall_size_mm':[extrema[i+3]-extrema[i] for i in range(3)],'body_count':len(doc.GetBodies2(0,False)),'model_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'drawing_acceptance':'AWAITING_USER_REVIEW','full_section_comparison':'NOT_RUN','from_zero_replay':'NOT_RUN','view':'custom isometric, global Z up'}
    (OUT/'basic_validation.json').write_text(json.dumps(report,indent=2),'utf-8')
    print(json.dumps(report),flush=True)
    return report

if __name__=='__main__':
    sw=b.TargetClient(); sw.connect(False,False)
    finish(sw)
