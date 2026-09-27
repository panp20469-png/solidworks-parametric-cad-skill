"""按读图合同建模；沿用已验证的二维面坐标转换和原生特征封装。"""
import sys, json, math, hashlib, traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent
OUT=HERE/'output'
LIB=HERE.parent/'elbow'/'elbow_clean_rebuild'
sys.path.insert(0,str(LIB))
import build_elbow_v10_spec as b
from sw_client import _get
import sw_client
# 此旧版封装把双向对称写成了 8；SolidWorks 的 swEndCondMidPlane 为 6。
sw_client.SW_END_MID_PLANE=6

contract=json.loads((HERE/'contract.json').read_text('utf-8'))
assert contract['gate']=='CONFIRMED'
used=set()
def d(i):
    key=f'D{i:02}'; used.add(key); return contract['dimensions'][key]
def vadd(a,c): return tuple(x+y for x,y in zip(a,c))
def sub(a,c): return tuple(x-y for x,y in zip(a,c))
def scale(a,k): return tuple(x*k for x in a)
def unit(a): return scale(a,1/math.hypot(*a))
def angle(a): return math.degrees(math.atan2(a[1],a[0]))
def line(a,c): return ('line',(a,c))
def arc(c,r,a,z,cw=False): return ('arc',(c,r,a,z,cw))
def circle(r): return [arc((0,0),r,0,180),arc((0,0),r,180,360)]

def rounded(points,radii):
    """按理论交点及局部圆角计算切点；不使用像素测量。"""
    joins=[]
    for i,p in enumerate(points):
        r=radii.get(i,0)
        if not r: joins.append((p,p,None)); continue
        incoming=unit(sub(p,points[i-1])); outgoing=unit(sub(points[(i+1)%len(points)],p))
        turn=math.atan2(incoming[0]*outgoing[1]-incoming[1]*outgoing[0],sum(x*y for x,y in zip(incoming,outgoing)))
        dist=r*math.tan(abs(turn)/2)
        a=vadd(p,scale(incoming,-dist)); z=vadd(p,scale(outgoing,dist))
        n=(-incoming[1],incoming[0]); c=vadd(a,scale(n,r*(1 if turn>0 else -1)))
        joins.append((a,z,arc(c,r,angle(sub(a,c)),angle(sub(z,c)),turn<0)))
    seg=[]
    for i,(a,z,curve) in enumerate(joins):
        prev=joins[i-1][1]
        if math.dist(prev,a)>1e-7: seg.append(line(prev,a))
        if curve: seg.append(curve)
    return seg

W=d(1)/2; pitch=d(2)/2; wallx=d(3)/2; slot=d(4)/2
rear=d(8); earfront=rear-d(5); slotbottom=rear-d(6); wallfront=slotbottom-d(7)
shoulder=earfront-d(9); front=shoulder-d(10); wing=d(11)/2; fw=d(12)/2
bossr=d(13)/2; mh=d(14)/2; sr=d(15); wr=d(16); rr=d(17); cr=d(18); outerr=d(19)
bore=d(20)/2; height=d(21); wh=d(22); mhheight=d(23); webt=d(24)
inside=d(25); outside=d(26); lugt=(outside-inside)/2; lugx=(outside+inside)/4
lughole=d(27)/2; rootr=d(28); assert abs(front+d(29))<1e-9
backcorner=d(30); thick=d(31); drop=d(32); lugr=d(33)/2; sider=d(34)
assert len(used)==len(contract['dimensions'])

basepts=[(-W,rear),(-slot,rear),(-slot,slotbottom),(slot,slotbottom),(slot,rear),(W,rear),(W,earfront),(wing,earfront),(wing,shoulder),(fw,shoulder),(fw,front),(-fw,front),(-fw,shoulder),(-wing,shoulder),(-wing,earfront),(-W,earfront)]
base=rounded(basepts,{2:sr,3:sr,7:rr,8:outerr,9:outerr,12:outerr,13:outerr,14:rr})
wallpts=[(-W,rear),(-slot,rear),(-slot,slotbottom),(slot,slotbottom),(slot,rear),(W,rear),(W,earfront),(wallx,earfront),(wallx,wallfront),(bossr,wallfront),(bossr,0),(-bossr,0),(-bossr,wallfront),(-wallx,wallfront),(-wallx,earfront),(-W,earfront)]
wall=rounded(wallpts,{2:sr,3:sr,7:rr,8:wr,9:cr,12:cr,13:wr,14:rr})

def tangent(p,right):
    c=(0,-drop); q=sub(p,c); length=math.hypot(*q)
    a=math.atan2(q[1],q[0]); offset=math.acos(lugr/length)
    candidates=[vadd(c,(lugr*math.cos(a+s*offset),lugr*math.sin(a+s*offset))) for s in (-1,1)]
    return (max if right else min)(candidates,key=lambda t:t[0])
tf=tangent((front,0),False); tb=tangent((backcorner,0),True)
u=unit(sub(tb,(backcorner,0))); n=(-u[1],u[0])
cc=(backcorner+(sider+sider*n[1])/n[0],-sider)
ct=vadd(cc,scale(n,-sider)); cs=(cc[0],0)
side=[line((front,0),cs),arc(cc,sider,90,angle(sub(ct,cc))),line(ct,tb),line(tb,tf),line(tf,(front,0))]

OUT.mkdir(exist_ok=True)
model=OUT/'drawing109.SLDPRT'; statepath=OUT/'state.json'; logpath=OUT/'build_log.json'
state=json.loads(statepath.read_text('utf-8')) if statepath.exists() else {'groups':[]}
log={'contract_sha256':hashlib.sha256((HERE/'contract.json').read_bytes()).hexdigest(),'consumed':sorted(used),'groups':[],'status':'RUNNING'}
sw=b.TargetClient()

def build_feature(segments,origin,ex,ey,depth,mid=False,cut=False):
    sk=state.get('pending_sketch')
    if not sk:
        sk=b.create_planar_3d_profile(sw,origin,ex,ey,segments)
        state['pending_sketch']=sk
        statepath.write_text(json.dumps(state,indent=2),'utf-8')
    result=b.extrude_sketch(sw,sk,depth,direction='through_all' if cut else ('mid_plane' if mid else 'blind'),is_cut=cut)
    state.pop('pending_sketch',None)
    return result
def planar(segments,y,depth): return build_feature(segments,(0,y,0),(1,0,0),(0,0,-1),depth)
def persist():
    sw.save_document(str(model))
    saved_doc=sw._app.ActiveDoc
    if str(_get(saved_doc,'GetPathName')).lower()!=str(model).lower():
        raise RuntimeError('Saved document path mismatch')
    sw.target_title=_get(saved_doc,'GetTitle')
    if not model.exists() or model.stat().st_size==0: raise RuntimeError('Native save missing')
    statepath.write_text(json.dumps(state,indent=2),'utf-8')
    logpath.write_text(json.dumps(log,indent=2,ensure_ascii=False),'utf-8')
def group(name,fn):
    if name in state['groups']: return
    print('GROUP='+name+'|START',flush=True)
    result=fn()
    doc=sw._active_doc(); doc.ForceRebuild3(False)
    bodies=doc.GetBodies2(0,False)
    if not bodies or len(bodies)!=1: raise RuntimeError(f'{name}: body count {len(bodies or [])}')
    log['groups'].append({'name':name,'result':str(result),'bodies':len(bodies)})
    state['groups'].append(name); persist()
    print('GROUP='+name+'|PASS',flush=True)

def root_fillet():
    doc=sw._active_doc(); body=doc.GetBodies2(0,False)[0]; doc.ClearSelection2(True); chosen=[]
    for edge in _get(body,'GetEdges'):
        curve=_get(edge,'GetCurve')
        if not _get(curve,'IsLine'): continue
        a=_get(edge,'GetStartVertex'); z=_get(edge,'GetEndVertex')
        if a is None or z is None: continue
        pa=[x*1000 for x in _get(a,'GetPoint')]; pz=[x*1000 for x in _get(z,'GetPoint')]
        if abs(pa[1])<.001 and abs(pz[1])<.001 and abs(abs(pa[0])-(lugx-webt/2))<.001 and abs(pa[0]-pz[0])<.001:
            adjacent=[f for f in _get(edge,'GetTwoAdjacentFaces2') if f is not None]
            # 后槽口与腹板共用合并平面，需确认另一侧是双腹板之间的中央底面。
            central_bottom=[]
            for face in adjacent:
                surf=_get(face,'GetSurface')
                if not _get(surf,'IsPlane'): continue
                normal=_get(face,'Normal'); box=[v*1000 for v in _get(face,'GetBox')]
                if normal[1]<-0.999 and box[0]>=-(lugx-webt/2)-.001 and box[3]<=(lugx-webt/2)+.001:
                    central_bottom.append(face)
            if not central_bottom:
                continue
            if not edge.Select4(True,_get(doc.SelectionManager,'CreateSelectData')): raise RuntimeError('Root edge selection failed')
            chosen.append([pa,pz])
    log['root_edges']=chosen
    if not chosen: raise RuntimeError('No inner root boundary found')
    for x in (-lugx+webt/2,lugx-webt/2):
        chain=[(min(a[2],z[2]),max(a[2],z[2])) for a,z in chosen if abs(a[0]-x)<.001]
        chain.sort()
        if not chain or abs(chain[0][0]+slotbottom+sr)>.001 or abs(chain[-1][1]+front)>.001:
            raise RuntimeError('Root boundary extent mismatch')
        if any(abs(a[1]-z[0])>.001 for a,z in zip(chain,chain[1:])):
            raise RuntimeError('Root boundary discontinuity')
    return sw.fillet(rootr,False)

try:
    sw.connect(False,False); log['pid']=b.verify_visible_instance(sw)
    if state['groups']:
        doc=sw._active_doc()
        if str(_get(doc,'GetPathName')).lower()!=str(model).lower(): raise RuntimeError('Resume requires the saved task document active')
        sw.target_title=_get(doc,'GetTitle')
    else:
        new=sw.create_part(); sw.target_title=new['title']
    group('01',lambda:planar(base,0,thick))
    group('02',lambda:planar(wall,thick,wh-thick))
    group('03',lambda:planar(circle(bossr),thick,height-thick))
    for label,x in [('04',-lugx),('06',lugx)]:
        group(label,lambda x=x:build_feature(side,(x,0,0),(0,0,-1),(0,1,0),webt,mid=True))
        group(str(int(label)+1).zfill(2),lambda x=x:build_feature(circle(lugr),(x,-drop,0),(0,0,-1),(0,1,0),lugt,mid=True))
    group('08',lambda:build_feature(circle(bore),(0,0,0),(1,0,0),(0,0,-1),height,cut=True))
    group('09',lambda:build_feature(circle(lughole),(0,-drop,0),(0,0,-1),(0,1,0),outside,cut=True))
    for label,x in [('10',-pitch),('11',pitch)]:
        group(label,lambda x=x:build_feature(circle(mh),(x,mhheight,0),(1,0,0),(0,1,0),rear,cut=True))
    group('12',root_fillet)
    log['geometry']=sw.check_geometry(); log['rebuild']=sw.rebuild_model()
    doc=sw._active_doc(); log['body_count']=len(doc.GetBodies2(0,False)); log['bounding_box']=list(doc.GetPartBox(True))
    _get(doc.ModelViewManager,'RemoveSectionView'); doc.ShowNamedView2('',7); _get(doc,'ViewZoomtofit2'); _get(doc,'GraphicsRedraw2')
    doc.SaveBMP(str(OUT/'drawing109.bmp'),1400,1000)
    log['status']='BASIC_CHECK_DONE'; log['drawing_match']='AWAITING_USER_REVIEW'; log['from_zero_replay']='NOT_RUN'
    persist(); print(json.dumps({'status':log['status'],'geometry':log['geometry'],'model':str(model)}),flush=True)
except Exception as exc:
    log['status']='FAILED'; log['error']=str(exc); log['traceback']=traceback.format_exc()
    logpath.write_text(json.dumps(log,indent=2,ensure_ascii=False),'utf-8')
    print('FIRST_ERROR='+str(exc),flush=True); raise
