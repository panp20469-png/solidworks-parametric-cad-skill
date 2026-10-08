"""按图纸合同建模；只连接已打开的 SolidWorks，按特征组保存并支持继续。"""
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
LIB = HERE.parent / 'elbow/elbow_clean_rebuild'
sys.path.insert(0, str(LIB))
import build_elbow_v10_spec as b
from sw_client import _get
import sw_client
sw_client.SW_END_MID_PLANE = 6

CONTRACT = HERE / 'contract.json'
C = json.loads(CONTRACT.read_text('utf-8'))
assert C['gate'] == 'CONFIRMED' and C['permission_to_generate_code']
used = set()
def d(key):
    used.add(key)
    return C['dimensions'][key]

H=d('total_height'); Z=d('port_height'); X=-d('port_axis_offset')
R=d('body_diameter')/2; RL=d('body_left_radius')
RI=d('cavity_left_diameter')/2; RC=d('cavity_right_radius')
HC=d('cavity_height'); CT=Z+RI; CB=CT-HC
W=d('base_width'); BT=d('base_thickness'); BR=d('base_corner_radius')
BP=d('base_hole_pitch'); BH=d('base_hole_diameter')/2
NR=d('bottom_neck_diameter')/2; NB=d('bottom_bore_diameter')/2
PT=d('port_total_length'); PH=d('port_half_length'); FT=d('port_flange_thickness')
PR=d('port_bore_diameter')/2; CN=d('c_neck_diameter')/2; DN=d('d_neck_diameter')/2
CF=d('c_flange_diameter')/2; CP=d('c_hole_pitch')
DF=d('d_flange_diameter')/2; ER=d('ear_radius'); FR=d('casting_fillet_radius'); CH=d('chamfer')
TM=d('upper_thread_major'); TP=d('upper_thread_pitch')
EM=d('ear_thread_major'); EP=d('ear_thread_pitch')
assert used == set(C['dimensions'])
assert PT == 2*PH and PH-FT > R
TI=(TM-5*math.sqrt(3)*TP/8)/2
EI=(EM-5*math.sqrt(3)*EP/8)/2
INNER=PH-FT
DX=[(DF*math.cos(math.radians(a)), DF*math.sin(math.radians(a))) for a in C['patterns']['d_angles_degrees']]
assert len(DX)==4 and C['patterns']['c_count']==2 and C['patterns']['base_count']==4

def line(a,z): return ('line',(a,z))
def arc(c,r,a,z,cw=False): return ('arc',(c,r,a,z,cw))
def circle(r,c=(0,0)): return [arc(c,r,0,180),arc(c,r,180,360)]
def angle(p,c=(0,0)): return math.degrees(math.atan2(p[1]-c[1],p[0]-c[0]))

base=[]
for a in (0,90,180,270):
    t=math.radians(a); n=math.radians(a+90)
    c=((W/2-BR)*(math.cos(t)-math.sin(t)),(W/2-BR)*(math.sin(t)+math.cos(t)))
    base.append(arc(c,BR,a,a+90))
    end=(c[0]+BR*math.cos(n),c[1]+BR*math.sin(n))
    nc=((W/2-BR)*(math.cos(n)-math.sin(n)),(W/2-BR)*(math.sin(n)+math.cos(n)))
    start=(nc[0]+BR*math.cos(n),nc[1]+BR*math.sin(n))
    base.append(line(end,start))

outer=[line((0,Z+RL),(X,Z+RL)),arc((X,Z),RL,90,270),line((X,Z-RL),(0,Z-RL)),line((0,Z-RL),(0,Z+RL))]
# φ30圆弧腔底与Z=39底面之间按R3求解相切过渡。
fc=(X+math.sqrt((RI+FR)**2-(CB-FR-Z)**2),CB-FR)
contact=(X+(fc[0]-X)*RI/(RI+FR),Z+(fc[1]-Z)*RI/(RI+FR))
inner=[line((0,CT),(X,CT)),arc((X,Z),RI,90,angle(contact,(X,Z))),arc(fc,FR,angle(contact,fc),90,True),line((fc[0],CB),(0,CB)),line((0,CB),(0,CT))]
right_inner=[line((0,-RC),(0,RC)),arc((0,0),RC,90,270,True)]
cprof=b.side_flange_profile(CF,ER,CP)
dprof=b.top_flange_profile(DF,ER,FR,DF,C['patterns']['d_angles_degrees'])

OUT=HERE/'output'
OUT.mkdir(exist_ok=True)
MODEL=OUT/'valve_LJT06_06.SLDPRT'
STATE=OUT/'state.json'; LOG=OUT/'build_log.json'
state=json.loads(STATE.read_text('utf-8')) if STATE.exists() else {'groups':{},'pending_sketch':None}
log={'contract_sha256':hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),'consumed':sorted(used),'attempts':[], 'mode':C['verification']['mode']}
if LOG.exists():
    old=json.loads(LOG.read_text('utf-8'))
    log['attempts']=old.get('attempts',[])
run={'started':time.strftime('%Y-%m-%dT%H:%M:%S'),'groups':[]}
log['attempts'].append(run)
sw=b.TargetClient()
current='attach'

def save():
    sw.save_document(str(MODEL))
    doc=sw._app.ActiveDoc
    sw.target_title=_get(doc,'GetTitle')
    if str(_get(doc,'GetPathName')).lower()!=str(MODEL).lower() or not MODEL.exists() or not MODEL.stat().st_size:
        raise RuntimeError('Native checkpoint missing or path mismatch')
    STATE.write_text(json.dumps(state,indent=2,ensure_ascii=False),'utf-8')
    LOG.write_text(json.dumps(log,indent=2,ensure_ascii=False),'utf-8')

def volume():
    bodies=sw._active_doc().GetBodies2(0,False) or []
    if not bodies: return 0.0
    return sw.get_mass_properties()['volume_mm3']

def feature(profile,origin,ex,ey,depth,mid=False,cut=False):
    sk=state.get('pending_sketch')
    if not sk:
        sk=b.create_planar_3d_profile(sw,origin,ex,ey,profile)
        state['pending_sketch']=sk
        STATE.write_text(json.dumps(state,indent=2,ensure_ascii=False),'utf-8')
    before=volume()
    if cut:
        # 双向对称且有明确深度的局部切除，防止旧封装退化为拉伸实体。
        b.select_sketch(sw,sk)
        doc=sw._active_doc()
        feat=doc.FeatureManager.FeatureCut3(True,False,False,6,0,depth/1000,0,False,False,False,False,0,0,False,False,False,False,False,True,True,False,False,False,0,0,False)
        if feat is None: raise RuntimeError('FeatureCut3 returned None')
        result=_get(feat,'Name')
    else:
        result=b.extrude_sketch(sw,sk,depth,direction='mid_plane' if mid else 'blind')
    after=volume()
    if (cut and after>=before-1e-5) or (not cut and after<=before+1e-5):
        raise RuntimeError(f'Volume change mismatch: {before} -> {after}, cut={cut}')
    state['pending_sketch']=None
    return {'feature':result,'before_mm3':before,'after_mm3':after}

def group(name,fn):
    global current
    current=name
    if name in state['groups']:
        saved=state['groups'][name]
        for fname in saved.get('feature_names',[]):
            if sw._active_doc().FeatureByName(fname) is None:
                raise RuntimeError('Resume feature missing: '+fname)
        return
    print('GROUP='+name+'|START',flush=True)
    result=fn()
    doc=sw._active_doc(); doc.ForceRebuild3(False)
    bodies=doc.GetBodies2(0,False)
    if len(bodies or [])!=1: raise RuntimeError('Expected one body')
    errors=sw.check_geometry()
    if errors.get('errors',0): raise RuntimeError('Feature errors: '+str(errors))
    names=[]
    if isinstance(result,dict) and result.get('feature'): names=[result['feature']]
    state['groups'][name]={'result':result,'feature_names':names,'body_count':len(bodies),'volume_mm3':volume()}
    run['groups'].append(name)
    save()
    print('GROUP='+name+'|PASS',flush=True)

def edge_circle(edge):
    cv=_get(edge,'GetCurve')
    if _get(cv,'IsCircle'):
        p=list(_get(cv,'CircleParams'))
        return [v*1000 for v in p[:3]],p[6]*1000
    return None

def edge_points(edge):
    vertices=[_get(edge,'GetStartVertex'),_get(edge,'GetEndVertex')]
    return [tuple(v*1000 for v in _get(t,'GetPoint')) for t in vertices if t is not None]

def fillet_by_test(test,label,minimum=1):
    doc=sw._active_doc(); doc.ClearSelection2(True)
    edges=[]
    for edge in _get(doc.GetBodies2(0,False)[0],'GetEdges'):
        cp=edge_circle(edge); pts=edge_points(edge)
        if test(cp,pts,edge):
            if not edge.Select4(True,_get(doc.SelectionManager,'CreateSelectData')): raise RuntimeError('Edge selection failed')
            edges.append({'circle':cp,'points':pts})
    run.setdefault('selected_edges',{})[label]=edges
    if len(edges)<minimum: raise RuntimeError('No required edges: '+label)
    result=sw.fillet(FR,label=='cavity_side_roots')
    result['edges']=len(edges)
    doc.ClearSelection2(True)
    return result

def main_cast_edges(cp,pts,e):
    if cp:
        c,r=cp
        if abs(r-NR)<1e-5 and (abs(c[2]-BT)<1e-5 or abs(c[2]-(Z-RL))<1e-5): return True
        if abs(r-R)<1e-5 and (abs(c[2]-(Z-RL))<1e-5 or abs(c[2]-(Z+RL))<1e-5): return True
        if abs(r-RL)<1e-5 and abs(abs(c[1])-R)<1e-5: return True
    if len(pts)==2:
        for z in (Z-RL,Z+RL):
            if all(abs(p[2]-z)<1e-5 for p in pts) and all(abs(abs(p[1])-R)<1e-5 for p in pts) and max(p[0] for p in pts)<=1e-5:
                return True
    return False

def neck_root_edges(cp,pts,e):
    if not cp: return False
    c,r=cp
    return abs(c[0]-X)<1e-5 and abs(c[2]-Z)<1e-5 and abs(abs(c[1])-R)<1e-5 and (abs(r-CN)<1e-5 or abs(r-DN)<1e-5)

def cavity_edges(cp,pts,e):
    # 限定腔侧壁与顶底交接；不触及外壳、安装板或后来生成的孔口。
    if cp:
        c,r=cp
        if abs(r-RC)<1e-5 and abs(c[0])<1e-5 and abs(c[1])<1e-5 and (abs(c[2]-CT)<1e-5 or abs(c[2]-CB)<1e-5): return True
    if len(pts)==2 and abs(pts[0][1]-pts[1][1])<1e-5 and all(abs(abs(p[1])-RC)<1e-5 for p in pts) and max(p[0] for p in pts)<=1e-5:
        if all(abs(p[2]-CT)<1e-5 for p in pts) or all(abs(p[2]-CB)<1e-5 for p in pts): return True
    return False

def threads():
    doc=sw._active_doc(); all_edges=list(_get(doc.GetBodies2(0,False)[0],'GetEdges'))
    chosen=[]
    for edge in all_edges:
        cp=edge_circle(edge)
        if not cp: continue
        c,r=cp
        if abs(r-TI)<1e-5 and abs(c[2]-H)<1e-5:
            chosen.append((edge,TM,TP,H-CT,'M36-6H'))
        elif abs(r-EI)<1e-5 and abs(abs(c[1])-PH)<1e-5:
            chosen.append((edge,EM,EP,FT,'M8'))
    if len(chosen)!=7: raise RuntimeError('Expected 7 thread entrance edges, found '+str(len(chosen)))
    results=[]
    for edge,major,pitch,depth,callout in chosen:
        doc.ClearSelection2(True)
        if not edge.Select4(False,_get(doc.SelectionManager,'CreateSelectData')): raise RuntimeError('Thread edge selection failed')
        f=doc.FeatureManager.InsertCosmeticThread3(8,'Tapped Hole',f'M{major}x{pitch}',major/1000,0,depth/1000,callout)
        if f is None: raise RuntimeError('Cosmetic thread failed: '+callout)
        results.append({'feature':_get(f,'Name'),'callout':callout,'pitch':pitch})
    doc.ClearSelection2(True)
    return {'threads':results}

def chamfers():
    doc=sw._active_doc(); chosen=[]; doc.ClearSelection2(True)
    for edge in _get(doc.GetBodies2(0,False)[0],'GetEdges'):
        cp=edge_circle(edge)
        if not cp: continue
        c,r=cp
        bottom=abs(c[2])<1e-5 and abs(r-NB)<1e-5 and abs(c[0])<1e-5 and abs(c[1])<1e-5
        mounting=abs(r-BH)<1e-5 and (abs(c[2])<1e-5 or abs(c[2]-BT)<1e-5) and abs(abs(c[0])-BP/2)<1e-5 and abs(abs(c[1])-BP/2)<1e-5
        port=abs(abs(c[1])-PH)<1e-5 and abs(r-PR)<1e-5 and abs(c[0]-X)<1e-5 and abs(c[2]-Z)<1e-5
        ear=abs(r-EI)<1e-5 and (abs(abs(c[1])-PH)<1e-5 or abs(abs(c[1])-INNER)<1e-5)
        top=abs(c[2]-H)<1e-5 and abs(r-TI)<1e-5
        if bottom or mounting or port or ear or top:
            if not edge.Select4(True,_get(doc.SelectionManager,'CreateSelectData')): raise RuntimeError('Chamfer selection failed')
            chosen.append(cp)
    run['chamfer_edges']=chosen
    if len(chosen)!=24: raise RuntimeError('Machined entrance edge count: '+str(len(chosen)))
    before=volume()
    # 使用本机swconst确认的实体倒角枚举：AngleDistance=1；旧封装误用了0。
    receipt=sw.chamfer(CH,45)
    feat=doc.FeatureByName(receipt['feature'])
    faces=_get(feat,'GetFaces') or []
    if len(faces)!=len(chosen) or volume()>=before-1e-5:
        raise RuntimeError('C1 chamfer did not produce the expected removed material and faces')
    for face in faces:
        rings=[edge_circle(e) for e in _get(face,'GetEdges') if edge_circle(e) is not None]
        if len(rings)!=2 or abs(abs(rings[0][1]-rings[1][1])-CH)>1e-6 or abs(math.dist(rings[0][0],rings[1][0])-CH)>1e-6:
            raise RuntimeError('Actual C1 radial/axial dimensions do not match the contract')
    result={'feature':_get(feat,'Name'),'distance_mm':CH,'angle_deg':45,'generated_faces':len(faces),'volume_removed_mm3':before-volume()}
    result['edges']=chosen
    return result

try:
    sw.connect(False,False); log['pid']=b.verify_visible_instance(sw)
    old=sw._app.ActiveDoc
    if state['groups'] or state.get('pending_sketch'):
        if old is None or str(_get(old,'GetPathName')).lower()!=str(MODEL).lower():
            raise RuntimeError('Resume requires the saved task document active')
        sw.target_title=_get(old,'GetTitle')
    else:
        if MODEL.exists(): raise RuntimeError('Existing model without state; refusing overwrite')
        log['preserved_document']=_get(old,'GetTitle') if old else None
        sw.target_title=sw.create_part()['title']
    if not state['groups'] and state.get('pending_sketch'):
        doc=sw._active_doc()
        extrusions=[f for f in sw.list_features() if f['type']=='Extrusion']
        expected=(W*W-(4-math.pi)*BR*BR)*BT
        if len(extrusions)!=1 or abs(volume()-expected)>0.001:
            raise RuntimeError('First checkpoint does not match the completed base')
        state['groups']['01']={'result':{'feature':extrusions[0]['name']},'feature_names':[extrusions[0]['name']],'body_count':1,'volume_mm3':volume()}
        state['pending_sketch']=None
        run['recovery']='Repair 1: use validated mass properties volume reader; recovered base matches analytical volume'
        save()
    group('01',lambda:feature(base,(0,0,0),(1,0,0),(0,1,0),BT))
    group('02',lambda:feature(circle(NR),(0,0,BT),(1,0,0),(0,1,0),Z-RL-BT))
    group('03',lambda:feature(circle(R),(0,0,Z-RL),(1,0,0),(0,1,0),H-(Z-RL)))
    group('04',lambda:feature(outer,(0,0,0),(1,0,0),(0,0,1),2*R,mid=True))
    group('04_fillet',lambda:fillet_by_test(main_cast_edges,'main_cast',6))
    group('05',lambda:feature(circle(CN),(X,R,Z),(1,0,0),(0,0,-1),INNER-R))
    group('06',lambda:feature(circle(DN),(X,-R,Z),(1,0,0),(0,0,1),INNER-R))
    group('07',lambda:feature(cprof,(X,INNER,Z),(1,0,0),(0,0,-1),FT))
    group('08',lambda:feature(dprof,(X,-INNER,Z),(1,0,0),(0,0,1),FT))
    group('09',lambda:fillet_by_test(neck_root_edges,'neck_body_roots',2))
    group('10',lambda:feature(inner,(0,0,0),(1,0,0),(0,0,1),2*RC,mid=True,cut=True))
    group('11',lambda:feature(right_inner,(0,0,(CT+CB)/2),(1,0,0),(0,1,0),HC,mid=True,cut=True))
    group('12',lambda:fillet_by_test(cavity_edges,'cavity_side_roots',4))
    group('13',lambda:feature(circle(NB),(0,0,CB/2),(1,0,0),(0,1,0),CB,mid=True,cut=True))
    group('14',lambda:feature(circle(TI),(0,0,(H+CT)/2),(1,0,0),(0,1,0),H-CT,mid=True,cut=True))
    group('15',lambda:feature(circle(PR),(X,0,Z),(1,0,0),(0,0,1),PT,mid=True,cut=True))
    group('16',lambda:feature(sum([circle(BH,(x,y)) for x in (-BP/2,BP/2) for y in (-BP/2,BP/2)],[]),(0,0,BT/2),(1,0,0),(0,1,0),BT,mid=True,cut=True))
    group('17',lambda:feature(sum([circle(EI,(x,0)) for x in (-CP/2,CP/2)],[]),(X,PH-FT/2,Z),(1,0,0),(0,0,1),FT,mid=True,cut=True))
    group('18',lambda:feature(sum([circle(EI,c) for c in DX],[]),(X,-PH+FT/2,Z),(1,0,0),(0,0,1),FT,mid=True,cut=True))
    group('19_threads',threads)
    group('20_chamfers',chamfers)
    import finish_edges
    for number,mode in enumerate(('c-root','d-root','d-back','c-back','machined_perimeters'),21):
        group(str(number),lambda mode=mode:finish_edges.apply(sw,C['dimensions'],mode))
    sw.set_custom_property('DrawingMaterial',C['metadata']['material'])
    sw.set_custom_property('ThreadRepresentation',C['metadata']['thread_representation'])
    sw.set_custom_property('DrawingNumber',C['part_id'])
    sw.set_custom_property('DrawingRequirements',json.dumps(C['metadata'],ensure_ascii=False))
    log['rebuild']=sw.rebuild_model(); log['geometry']=sw.check_geometry()
    doc=sw._active_doc()
    log['body_count']=len(doc.GetBodies2(0,False) or [])
    log['bounding_box_mm']=[v*1000 for v in doc.GetPartBox(True)]
    log['volume_mm3']=volume()
    if not log['rebuild']['rebuilt'] or log['geometry']['errors'] or log['body_count']!=1: raise RuntimeError('Final basic check failed')
    doc.ClearSelection2(True)
    # 草图和参考面仅为构造依据，不遮挡交付模型。
    f=_get(doc,'FirstFeature')
    while f:
        typ=_get(f,'GetTypeName2')
        if typ in ('3DProfileFeature','ProfileFeature','RefPlane'):
            doc.ClearSelection2(True)
            if f.Select2(False,0):
                _get(doc,'BlankRefGeom' if typ=='RefPlane' else 'BlankSketch')
        f=_get(f,'GetNextFeature')
    doc.ClearSelection2(True)
    sw.set_view_orientation('isometric')
    sw.set_display_mode('shaded_with_edges')
    _get(doc,'ViewZoomtofit2'); _get(doc,'GraphicsRedraw2')
    doc.SaveBMP(str(OUT/'valve_isometric.bmp'),1400,1050)
    run['status']='BASIC_CHECK_PASS'
    log['status']='BASIC_CHECK_PASS'; log['drawing_acceptance']='AWAITING_USER_REVIEW'
    log['from_zero_replay']='NOT_RUN'
    save()
    import importlib.util
    module_spec=importlib.util.spec_from_file_location('final_check',HERE/'final_check.py')
    final_check=importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(final_check)
    final_check.finish(sw)
    print('RESULT=BASIC_CHECK_PASS|MODEL='+str(MODEL),flush=True)
except Exception as exc:
    run['status']='FAILED'; run['first_error']={'group':current,'error':str(exc),'traceback':traceback.format_exc()}
    log['status']='FAILED'
    try:
        if sw.target_title: save()
    except Exception as save_exc:
        run['checkpoint_error']=str(save_exc)
    LOG.write_text(json.dumps(log,indent=2,ensure_ascii=False),'utf-8')
    print('FIRST_ERROR|GROUP='+current+'|'+str(exc),flush=True)
    raise
