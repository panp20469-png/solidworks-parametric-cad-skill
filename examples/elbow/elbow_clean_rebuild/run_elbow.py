"""本案例从空白零件复现；只基础验收，不启动 SW 或生成剖面。"""
import json
import math
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_elbow_v10_spec as b
from finish_elbow_v10_threads import finish_threads
from sw_client import _get


def junction_fillets(sw, spec, top_end, upper, start_group=0):
    doc = sw._active_doc()
    branch = (math.cos(math.radians(spec['side_branch']['axis_angle_deg'])),
              math.sin(math.radians(spec['side_branch']['axis_angle_deg'])), 0)
    origin = (spec['side_branch']['axis_origin_x'], spec['side_branch']['axis_center_height'], 0)
    cback = b.add(origin, b.mul(branch, spec['side_branch']['visible_pipe_length']))
    results = []
    for pairs, expected in [([{'bend','side'}, {'upper','Bback'}, {'side','Cback'}],3),
                             ([{'main','base'}, {'main','boss'}, {'base','boss'}],4)][start_group:]:
        body = doc.GetBodies2(0,False)[0]
        faces = list(_get(body,'GetFaces'))
        tags = []
        for face in faces:
            surf = _get(face,'GetSurface')
            tag = ''
            if _get(surf,'IsCylinder'):
                p = _get(surf,'CylinderParams')
                for label,axis,radius in [('main',(0,1,0),spec['main_tube']['outer_diameter']/2),
                                           ('upper',upper,spec['main_tube']['outer_diameter']/2),
                                           ('side',branch,spec['side_branch']['outer_diameter']/2),
                                           ('boss',(0,0,1),spec['front_boss']['outer_diameter']/2)]:
                    if abs(p[6]*1000-radius)<1e-5 and abs(abs(b.dot(p[3:6],axis))-1)<1e-7:
                        tag=label
            elif _get(surf,'IsTorus'):
                p = _get(surf,'TorusParams')
                if abs(p[6]*1000-spec['main_tube']['path']['arc_radius'])<1e-5 and abs(p[7]*2000-spec['main_tube']['outer_diameter'])<1e-5:
                    tag='bend'
            elif _get(surf,'IsPlane'):
                p = _get(surf,'PlaneParams')
                for label,axis,point in [('base',(0,1,0),(0,spec['base']['thickness'],0)),
                                          ('Bback',upper,top_end),('Cback',branch,cback)]:
                    delta=tuple(p[i+3]*1000-point[i] for i in range(3))
                    if abs(abs(b.dot(p[:3],axis))-1)<1e-7 and abs(b.dot(delta,axis))<1e-5:
                        tag=label
            tags.append(tag)
        doc.ClearSelection2(True)
        selected=[]
        # 先缓存面的几何分类，再按相邻面配对选边，不依赖易变的边序号。
        for edge in _get(body,'GetEdges'):
            edge_tags=set()
            for adj in _get(edge,'GetTwoAdjacentFaces2'):
                if adj is not None:
                    index=next((i for i,f in enumerate(faces) if f._oleobj_==adj._oleobj_),None)
                    if index is not None:
                        edge_tags.add(tags[index])
            if edge_tags in pairs:
                if not edge.Select4(True,_get(doc.SelectionManager,'CreateSelectData')):
                    raise RuntimeError('Junction edge selection failed')
                selected.append(sorted(edge_tags))
        if len(selected)!=expected:
            raise RuntimeError(f'Junction selection mismatch: {selected}')
        results.append({'selection':selected,'result':sw.fillet(3,False)})
    doc.ClearSelection2(True)
    return results


def main(on_new_document=None):
    started=time.perf_counter()
    b.OUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix=datetime.now().strftime('%Y%m%d_%H%M%S')
    output=b.OUT_DIR / ('elbow_436_from_zero_'+suffix+'.SLDPRT')
    logpath=output.with_suffix('.json')
    if output.exists():
        raise RuntimeError('Refusing to overwrite existing part')
    spec=json.loads(b.SPEC_PATH.read_text(encoding='utf-8'))
    if any(not row.passed for row in b.validate_spec(spec)):
        raise RuntimeError('Drawing contract preflight failed')
    contract=b.SpecContract(spec)
    groups=[]; receipts={}; ready=False
    sw=b.TargetClient()
    report={'output':str(output),'groups':groups,'verification_mode':'basic_plus_human_acceptance',
            'spec_sha256':b.sha256(b.SPEC_PATH),'drawing_match':'AWAITING_USER_REVIEW'}
    try:
        sw.connect(False,False)
        report['pid']=b.verify_visible_instance(sw)
        old=sw._app.ActiveDoc
        report['preserved_document']=_get(old,'GetPathName') if old is not None else None
        new=sw.create_part()
        doc=sw._active_doc()
        if old is not None and doc._oleobj_==old._oleobj_:
            raise RuntimeError('New document did not become active')
        sw.target_title=new['title']; ready=True
        print('New blank document ready',flush=True)
        if on_new_document is not None:
            on_new_document(sw, output)
        b.make_base(sw,contract,groups)
        top_end,upper=b.make_main_tube(sw,contract,groups)
        print('Base and main tube built',flush=True)
        b.make_top_flange(sw,contract,top_end,upper,groups)
        b.make_side_branch(sw,contract,groups,receipts)
        b.make_front_boss(sw,contract,groups,receipts)
        b.cut_main_passage(sw,contract);groups.append('group_07')
        contract.assert_required_used()
        print('Primary geometry built; applying proven finishing operations',flush=True)
        report['fillets']=junction_fillets(sw,spec,top_end,upper)
        report['threads']=finish_threads(sw)
        sw.set_custom_property('DrawingMaterial','HT200')
        sw.set_custom_property('MaterialVerification','Drawing grade only; physical material database not assigned')
        sw.set_custom_property('DrawingSurfaceFinish','Ra6.3 on indicated machined surfaces')
        report['rebuild']=sw.rebuild_model()
        report['geometry']=sw.check_geometry()
        report['body_count']=len(sw.list_bodies())
        if not report['rebuild']['rebuilt'] or report['geometry']['errors'] or report['body_count']!=1:
            raise RuntimeError('Basic geometry check failed')
        report['orientation']=sw.set_view_orientation('isometric')
        report['saved']=sw.save_document(str(output))
        sw.target_title=_get(doc,'GetTitle')
        report['screenshot']=sw.capture_screenshot(str(output.with_suffix('.bmp')))
        report['status']='BASIC_CHECK_PASS'
        report['elapsed_seconds']=round(time.perf_counter()-started,2)
        logpath.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=True),flush=True)
        return 0
    except Exception as exc:
        report['status']='FAILED';report['error']=str(exc)
        report['elapsed_seconds']=round(time.perf_counter()-started,2)
        # 失败时保留现场，不创建第二个测试零件，不导出 STEP。
        if ready:
            try: report['checkpoint']=sw.save_document(str(output))
            except Exception as save_error: report['checkpoint_error']=str(save_error)
        logpath.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=True),flush=True)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
