"""仅以实测曲面/边界核验合同；生成器状态只用于定位特征，不作为尺寸证据。"""
import hashlib
import json
import math
from pathlib import Path

CASE=Path(__file__).resolve().parents[1]
OUT=CASE/'output/full_validation'
C=json.loads((CASE/'contract.json').read_text('utf-8'));P=C['dimensions']
data=json.loads((OUT/'measurements.json').read_text('utf-8'))
F=data['faces'];features=json.loads((OUT/'features.json').read_text('utf-8'))
state=json.loads((CASE/'output/state.json').read_text('utf-8'))['groups']
model=CASE/'output/valve_LJT06_06.SLDPRT'
assert hashlib.sha256(model.read_bytes()).hexdigest()==data['model_sha256']
TOL=.001;rows=[];covered=set()

def equal(a,b):
    if isinstance(a,(list,tuple)):
        return isinstance(b,(list,tuple)) and len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
    if isinstance(a,(str,bool)) or a is None:return a==b
    return isinstance(b,(float,int)) and abs(a-b)<=TOL

def check(label,actual,expected,faces=(),keys=()):
    covered.update(keys)
    rows.append({'id':len(rows)+1,'label':label,'actual':actual,'expected':expected,'face_ids':[f['id'] for f in faces],'contract_keys':list(keys),'status':'PASS' if equal(actual,expected) else 'FAIL'})

def group(g,kind=None):
    name=state[g]['result']['feature']
    return [f for f in F if f['owner']==name and (kind is None or f.get('type')==kind)]

def radius(f):return f['params_si'][6]*1000
def center(f):return [x*1000 for x in f['params_si'][:3]]
def axis(f):return [abs(x) for x in f['params_si'][3:6]]
def plane(f,a):return f['params_si'][a+3]*1000
def circles(f):return [e['circle_si'] for e in f['edges'] if 'circle_si' in e]
def span(f,a):
    v=[p[a] for e in f['edges'] for p in (e['start'],e['end']) if p is not None]
    v += [c[a]*1000 for c in circles(f) if abs(abs(c[a+3])-1)<1e-6]
    return [min(v),max(v)]
def one(g,kind):
    fs=group(g,kind);assert len(fs)==1,(g,kind,len(fs));return fs[0]
def planes(g,a):return sorted((f for f in group(g,'plane') if abs(abs(f['params_si'][a])-1)<1e-6),key=lambda f:plane(f,a))
def diam(g,key):
    fs=group(g,'cylinder');assert fs,(g,key)
    check(key,[2*radius(f) for f in fs],[P[key]]*len(fs),fs,[key]);return fs

base=planes('01',2);check('底板上下加工面位置',[plane(f,2) for f in base],[0,P['base_thickness']],base,['base_thickness'])
for a in (0,1):
    fs=planes('01',a);check('底板外宽轴'+str(a),[plane(f,a) for f in fs],[-P['base_width']/2,P['base_width']/2],fs,['base_width'])
fs=group('01','cylinder');check('底板四角半径',[radius(f) for f in fs],[P['base_corner_radius']]*4,fs,['base_corner_radius'])
check('四角圆心',sorted([center(f)[:2] for f in fs]),sorted([[x,y] for x in (-25,25) for y in (-25,25)]),fs)
neck=one('02','cylinder');check('下颈直径',2*radius(neck),P['bottom_neck_diameter'],[neck],['bottom_neck_diameter'])
outer=one('03','cylinder');check('主体外径',2*radius(outer),P['body_diameter'],[outer],['body_diameter'])
top=planes('03',2);check('主体上下理论端面',[plane(f,2) for f in top],[P['port_height']-P['body_left_radius'],P['total_height']],top,['total_height'])
left=one('04','cylinder');check('主体左端R20',radius(left),P['body_left_radius'],[left],['body_left_radius'])
check('左端外圆轴心XZ',[center(left)[0],center(left)[2]],[-P['port_axis_offset'],P['port_height']],[left],['port_axis_offset','port_height'])
fs=planes('04',1);check('主体横向宽60',[plane(f,1) for f in fs],[-P['body_diameter']/2,P['body_diameter']/2],fs)
cn=diam('05','c_neck_diameter');dn=diam('06','d_neck_diameter')
for fs in (cn,dn):check('端颈与横孔共轴',[[center(f)[0],center(f)[2]] for f in fs],[[-P['port_axis_offset'],P['port_height']]]*len(fs),fs)
for g,sign in [('07',1),('08',-1)]:
    fs=planes(g,1)
    actual=sorted(set(round(plane(f,1),8) for f in fs))
    check(g+'端法兰厚度及位置',actual,sorted([sign*(P['port_half_length']-P['port_flange_thickness']),sign*P['port_half_length']]),fs,['port_half_length','port_flange_thickness'])
check('两端加工面总距',max(plane(f,1) for f in planes('07',1))-min(plane(f,1) for f in planes('08',1)),P['port_total_length'],planes('07',1)+planes('08',1),['port_total_length'])
for g,key in [('07','c_flange_diameter'),('08','d_flange_diameter')]:
    fs=[f for f in group(g,'cylinder') if abs(center(f)[0]+P['port_axis_offset'])<TOL and abs(center(f)[2]-P['port_height'])<TOL]
    check(key,[2*radius(f) for f in fs],[P[key]]*(2 if g=='07' else 4),fs,[key])
    ears=[f for f in group(g,'cylinder') if abs(radius(f)-P['ear_radius'])<.5]
    check(g+'耳外缘R8',[radius(f) for f in ears],[P['ear_radius']]*(2 if g=='07' else 4),ears,['ear_radius'])
    if g=='08':
        blends=[f for f in group(g,'cylinder') if radius(f)<5]
        check('D端八处轮廓R3',[radius(f) for f in blends],[P['casting_fillet_radius']]*8,blends,['casting_fillet_radius'])

floor=P['port_height']+P['cavity_left_diameter']/2-P['cavity_height'];roof=floor+P['cavity_height']
fs=planes('10',2);check('主腔底面与顶面高度',[plane(f,2) for f in fs],[floor,roof],fs,['cavity_height'])
fs=planes('10',1);check('主腔侧壁位置及宽度',[plane(f,1) for f in fs],[-P['cavity_right_radius'],P['cavity_right_radius']],fs)
fs=group('10','cylinder');large=max(fs,key=radius);small=min(fs,key=radius)
check('左侧圆弧腔直径',2*radius(large),P['cavity_left_diameter'],[large],['cavity_left_diameter'])
check('左腔圆弧轴心',[center(large)[0],center(large)[2]],[-P['port_axis_offset'],P['port_height']],[large])
check('左腔局部最低点',center(large)[2]-radius(large),35,[large])
check('左腔底R3相切圆弧',radius(small),P['casting_fillet_radius'],[small])
check('左腔两圆弧外切',math.dist([center(large)[i] for i in (0,2)],[center(small)[i] for i in (0,2)]),radius(large)+radius(small),[large,small])
right=one('11','cylinder');check('主腔右端R20',radius(right),P['cavity_right_radius'],[right],['cavity_right_radius'])
check('主腔右端与上下口同轴',center(right)[:2],[0,0],[right])
bottom=one('13','cylinder');upper=one('14','cylinder')
check('下孔25H7名义直径',2*radius(bottom),P['bottom_bore_diameter'],[bottom],['bottom_bore_diameter'])
check('上下口及外颈共轴',[center(f)[:2] for f in (neck,outer,bottom,upper)],[[0,0]]*4,[neck,outer,bottom,upper])
check('M36基本小径',2*radius(upper),P['upper_thread_major']-5*math.sqrt(3)*P['upper_thread_pitch']/8,[upper],['upper_thread_major','upper_thread_pitch'])
check('下孔接腔且孔口留C1',span(bottom,2),[P['chamfer'],floor],[bottom])
check('上孔接腔且孔口留C1',span(upper,2),[roof,P['total_height']-P['chamfer']],[upper])
ports=sorted(group('15','cylinder'),key=lambda f:span(f,1)[0])
check('两端16H7名义孔径',[2*radius(f) for f in ports],[P['port_bore_diameter']]*2,ports,['port_bore_diameter'])
check('横孔轴线XZ',[[center(f)[0],center(f)[2]] for f in ports],[[-P['port_axis_offset'],P['port_height']]]*2,ports)
check('横孔两端接腔边界',[span(f,1) for f in ports],[[-P['port_half_length']+P['chamfer'],-P['cavity_right_radius']],[P['cavity_right_radius'],P['port_half_length']-P['chamfer']]],ports)

def shared_circle(bore,wall,axis_index,coordinate):
    a=[c for c in circles(bore) if abs(c[axis_index]*1000-coordinate)<TOL]
    bcs=[c for f in wall for c in circles(f)]
    return any(math.dist(c[:3],w[:3])*1000<TOL and abs(c[6]-w[6])*1000<TOL for c in a for w in bcs)
check('下孔与主腔共用开口边界',shared_circle(bottom,planes('10',2),2,floor),True,[bottom]+planes('10',2))
check('上孔与主腔共用开口边界',shared_circle(upper,planes('10',2),2,roof),True,[upper]+planes('10',2))
for f,y in zip(ports,[-P['cavity_right_radius'],P['cavity_right_radius']]):check('横孔与主腔共用开口边界 '+str(y),shared_circle(f,planes('10',1),1,y),True,[f]+planes('10',1))

holes=group('16','cylinder');check('四安装孔直径',[2*radius(f) for f in holes],[P['base_hole_diameter']]*4,holes,['base_hole_diameter'])
check('四安装孔50方阵',sorted([center(f)[:2] for f in holes]),sorted([[x,y] for x in (-P['base_hole_pitch']/2,P['base_hole_pitch']/2) for y in (-P['base_hole_pitch']/2,P['base_hole_pitch']/2)]),holes,['base_hole_pitch'])
check('四安装孔仅贯穿底板',[span(f,2) for f in holes],[[P['chamfer'],P['base_thickness']-P['chamfer']]]*4,holes)
for g,count,sign in [('17',2,1),('18',4,-1)]:
    fs=group(g,'cylinder')
    check(g+'M8基本小径',[2*radius(f) for f in fs],[P['ear_thread_major']-5*math.sqrt(3)*P['ear_thread_pitch']/8]*count,fs,['ear_thread_major','ear_thread_pitch'])
    coords=sorted([[center(f)[0]+P['port_axis_offset'],center(f)[2]-P['port_height']] for f in fs])
    expected=sorted([[-P['c_hole_pitch']/2,0],[P['c_hole_pitch']/2,0]]) if g=='17' else sorted([[P['d_flange_diameter']/2*math.cos(math.radians(a)),P['d_flange_diameter']/2*math.sin(math.radians(a))] for a in C['patterns']['d_angles_degrees']])
    check(g+'耳孔中心位置',coords,expected,fs,['c_hole_pitch'] if g=='17' else [])
    bounds=sorted([sign*(P['port_half_length']-P['chamfer']),sign*(P['port_half_length']-P['port_flange_thickness']+P['chamfer'])])
    check(g+'耳孔仅贯穿法兰',[span(f,1) for f in fs],[bounds]*count,fs)
    ears=[f for f in group('07' if g=='17' else '08','cylinder') if abs(radius(f)-P['ear_radius'])<.5]
    check(g+'耳孔与耳外圆共轴',sorted([[center(f)[0],center(f)[2]] for f in fs]),sorted([[center(f)[0],center(f)[2]] for f in ears]),fs+ears)
for g,a in [('13',2),('14',2),('15',1),('16',2),('17',1),('18',1)]:
    fs=group(g,'cylinder');expected=[0,0,0];expected[a]=1
    check(g+'孔轴方向',[axis(f) for f in fs],[expected]*len(fs),fs)
threads=[f for f in features if f['type']=='CosmeticThread']
check('装饰螺纹数量',len(threads),7)
check('螺纹公称直径',sorted([f['Diameter']*1000 for f in threads]),sorted([P['upper_thread_major']]+[P['ear_thread_major']]*6))
check('螺纹标注',sorted([f['ThreadCallout'] for f in threads]),sorted(['M36-6H']+['M8']*6))
check('螺纹长度',sorted([f['BlindDepth']*1000 for f in threads]),sorted([P['total_height']-roof]+[P['port_flange_thickness']]*6))
fillets=[f for f in features if f['type']=='Fillet'];check('七组圆角实际定义R3',[f['DefaultRadius']*1000 for f in fillets],[P['casting_fillet_radius']]*7)
torus=[f for f in F if f.get('type')=='torus'];check('所有圆环过渡实际小半径',[f['params_si'][7]*1000 for f in torus],[P['casting_fillet_radius']]*len(torus),torus)
for g in ('21','22','23','24'):
    fs=group(g);check(g+'补充R3存在真实曲面',bool(fs),True,fs)

for g,count in [('20_chamfers',24),('25',41)]:
    fs=group(g);check(g+'实际倒角面数量',len(fs),count,fs,['chamfer'])
    errors=[];details=[]
    for f in fs:
        cs=circles(f)
        if len(cs)==2:
            axial=math.dist(cs[0][:3],cs[1][:3])*1000
            radial=abs(cs[0][6]-cs[1][6])*1000
            error=max(abs(axial-P['chamfer']),abs(radial-P['chamfer']))
            details.append({'face':f['id'],'axial_mm':axial,'radial_mm':radial})
        elif f.get('type')=='plane':
            vertices=[p for e in f['edges'] for p in (e['start'],e['end']) if p is not None]
            normal=f['params_si'][:3]
            candidates=[]
            for a in (1,2):
                width=max(p[a] for p in vertices)-min(p[a] for p in vertices)
                if abs(abs(normal[a])-math.sqrt(.5))<1e-5:candidates.append(abs(width-P['chamfer']))
            error=min(candidates) if candidates else 999
            details.append({'face':f['id'],'width_error_mm':error,'normal':normal})
        else:error=999;details.append({'face':f['id'],'unsupported':True})
        errors.append(error)
    check(g+'C1逐面径向/轴向或平面45度核验',max(errors),0,fs)
    rows[-1]['details']=details
check('单实体',data['body_count'],C['verification']['body_count'])
check('合同全部数值尺寸有检查',sorted(covered),sorted(P))
report={'mode':'full_drawing_match','model_sha256':data['model_sha256'],'contract_sha256':hashlib.sha256((CASE/'contract.json').read_bytes()).hexdigest(),'tolerance_mm':TOL,'scope':'名义几何的独立实体测量；制造公差及实际材料性能不在此数值检查范围内','rows':rows,'passed':sum(r['status']=='PASS' for r in rows),'failed':sum(r['status']=='FAIL' for r in rows)}
(OUT/'checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({'checks':len(rows),'passed':report['passed'],'failed':[{'id':r['id'],'label':r['label'],'actual':r['actual'],'expected':r['expected']} for r in rows if r['status']!='PASS']},ensure_ascii=True))
if report['failed']:raise SystemExit(1)
