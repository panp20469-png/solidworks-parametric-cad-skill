"""从实体解析面及边界测量复核弯头；编号只适用于已记录的模型快照。"""
import math,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/demo/elbow-validation'
SPEC=ROOT/'examples/elbow/elbow_clean_rebuild/elbow_v10_spec.json'
s=json.loads(SPEC.read_text('utf-8'));m=json.loads((OUT/'measurements.json').read_text('utf-8'));F={f['id']:f for f in m['faces']}
features=json.loads((OUT/'features.json').read_text('utf-8'));rows=[];tol=.001
def p(i):return F[i]['params_si']
def xyz(i):return [v*1000 for v in p(i)[:3]]
def rad(i):return p(i)[6]*1000
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def sub(a,b):return [x-y for x,y in zip(a,b)]
def mul(a,t):return [x*t for x in a]
def add(a,b):return [x+y for x,y in zip(a,b)]
def norm(a):return math.sqrt(dot(a,a))
def plane(i,axis,origin=(0,0,0)):
 assert abs(abs(dot(p(i)[:3],axis))-1)<1e-7
 return dot(sub([x*1000 for x in p(i)[3:6]],origin),axis)
def compare(a,b,t):
 if isinstance(a,list):return len(a)==len(b) and all(compare(x,y,t) for x,y in zip(a,b))
 if isinstance(a,str):return a==b
 return abs(a-b)<=t
def ck(label,actual,expected,ids=(),t=tol):rows.append({'id':f'E{len(rows)+1:02}','label':label,'actual':actual,'expected':expected,'faces':list(ids),'tolerance':t,'status':'PASS' if compare(actual,expected,t) else 'FAIL'})
def diam(label,ids,expected):ck(label,[rad(i)*2 for i in ids],[expected]*len(ids),ids)
def ranges(i,axis,origin=(0,0,0)):
 values=[]
 for e in F[i]['edges']:
  for point in [e['start'],e['end']]:
   if point is not None:values.append(dot(sub(point,origin),axis))
  c=e.get('circle_si')
  if c and abs(abs(dot(c[3:6],axis))-1)<1e-7:values.append(dot(sub([v*1000 for v in c[:3]],origin),axis))
 return [min(values),max(values)]
X=[1,0,0];Y=[0,1,0];Z=[0,0,1];U=[-2**-.5,2**-.5,0];C=[3**.5/2,.5,0];B=s['base'];M=s['main_tube'];T=s['top_flange'];S=s['side_branch'];G=s['front_boss'];co=[0,S['axis_center_height'],0]
ck('底座宽',plane(6,X)-plane(10,X),B['width'],[6,10]);ck('底座深',plane(4,Z)-plane(8,Z),B['depth'],[4,8]);ck('底座厚',plane(11,Y)-plane(12,Y),B['thickness'],[11,12])
ck('底座四角 R10',[rad(i) for i in [3,5,7,9]],[B['corner_radius']]*4,[3,5,7,9])
diam('底座四孔 Φ8',[13,14,15,16],B['mounting_holes']['diameter'])
ck('底座孔数',len([f for f in F.values() if f.get('type')=='cylinder' and abs(abs(dot(f['params_si'][3:6],Y))-1)<1e-7 and abs(f['params_si'][6]*1000-4)<tol]),4)
ck('底座四孔 XZ 位置',sorted([[xyz(i)[0],xyz(i)[2]] for i in [13,14,15,16]]),[[-20,-20],[-20,20],[20,-20],[20,20]],[13,14,15,16])
ck('底座四孔贯穿范围',[ranges(i,Y) for i in [13,14,15,16]],[[0,B['thickness']]]*4,[13,14,15,16])
diam('主管上下直段外径',[17,19],M['outer_diameter']);diam('主管上下直段内径',[54,34],M['inner_diameter'])
ck('弯管内外中心线 R35',[p(i)[6]*1000 for i in [18,53]],[M['path']['arc_radius']]*2,[18,53])
ck('弯管中心坐标',[xyz(i) for i in [18,53]],[M['path']['arc_center']+[0]]*2,[18,53])
ck('弯管内外半径与壁厚',[p(18)[7]*1000,p(53)[7]*1000,(p(18)[7]-p(53)[7])*1000],[20,15,5],[18,53])
ck('下主管轴线 XZ',[[xyz(i)[j] for j in [0,2]] for i in [17,54]],[[0,0]]*2,[17,54])
ck('主管上下轴向',[p(i)[3:6] for i in [17,19]],[Y,U],[17,19])
ck('主管上段方向角',math.degrees(math.atan2(p(19)[4],p(19)[3])),M['path']['upper_direction_deg'],[19],.001)
ck('下直段与内弯管连接高',ranges(54,Y)[1],M['path']['arc_center'][1],[54])
ck('下主管通到底面',ranges(54,Y)[0],0,[54])
# 用真实上管轴线与 B 后端面相交，恢复 80 mm 的尺寸基准。
uaxis=xyz(19);t=plane(20,U)-dot(uaxis,U);back=add(uaxis,mul(U,t));front=add(back,mul(U,plane(21,U)-plane(20,U)))
ck('B 后端中心高度',back[1],M['path']['top_height'],[19,20])
ck('B 法兰厚度',plane(21,U)-plane(20,U),T['thickness'],[21,20])
diam('B 法兰主体 Φ56',[23,27,31],T['body_diameter']);ck('B 三耳 R10',[rad(i) for i in [25,29,33]],[T['lug_radius']]*3,[25,29,33]);ck('B 六处轮廓 R5',[rad(i) for i in [22,24,26,28,30,32]],[T['transition_radius']]*6,[22,24,26,28,30,32])
diam('B 三孔 Φ8',[35,36,37],T['hole_diameter'])
ck('B Φ8 圆柱面数',len([f for f in F.values() if f.get('type')=='cylinder' and abs(abs(dot(f['params_si'][3:6],U))-1)<1e-7 and abs(f['params_si'][6]*1000-4)<tol]),3)
vectors=[sub(sub(xyz(i),back),mul(U,dot(sub(xyz(i),back),U))) for i in [35,36,37]]
ck('B 孔中心节圆半径',[norm(v) for v in vectors],[T['pitch_radius']]*3,[35,36,37])
ck('B 孔相邻角度',[math.degrees(math.acos(max(-1,min(1,dot(vectors[i],vectors[(i+1)%3])/(norm(vectors[i])*norm(vectors[(i+1)%3])))))) for i in range(3)],[T['angular_spacing_deg']]*3,[35,36,37],.001)
ck('B 三孔贯穿厚度',[ranges(i,U,back) for i in [35,36,37]],[[0,T['thickness']]]*3,[35,36,37])
ck('B 主体与上主管共轴',[norm(sub(sub(xyz(i),back),mul(U,dot(sub(xyz(i),back),U)))) for i in [23,27,31,34]],[0]*4,[23,27,31,34])
ck('上主管通至法兰外面',ranges(34,U,back)[1],T['thickness'],[34])
diam('侧支管外径',[38],S['outer_diameter']);diam('侧支管内径',[1],S['inner_diameter'])
ck('侧支管轴高',xyz(38)[1],S['axis_center_height'],[38]);ck('侧支管轴向',p(38)[3:6],C,[38]);ck('侧支管轴线基准',xyz(38),co,[38])
ck('侧支管 25 尺寸端点',plane(0,C,co),S['visible_pipe_length'],[0]);ck('侧法兰厚 6',plane(47,C,co)-plane(0,C,co),S['flange']['thickness'],[47,0]);ck('侧法兰总轴向位置',plane(47,C,co),S['visible_pipe_length']+S['flange']['thickness'],[47])
ck('C 中央轮廓 R12',[rad(i) for i in [41,45]],[S['flange']['center_radius']]*2,[41,45]);ck('C 两耳 R6',[rad(i) for i in [39,43]],[S['flange']['ear_radius']]*2,[39,43])
ck('C 中孔与支管共轴',[norm(sub(sub(xyz(i),co),mul(C,dot(sub(xyz(i),co),C)))) for i in [1,38,41,45]],[0]*4,[1,38,41,45])
ck('M6 底孔孔距',abs(xyz(49)[2]-xyz(50)[2]),S['flange']['hole_pitch'],[49,50]);diam('M6 底孔 Φ5',[49,50],5)
ck('两螺纹底孔轴向范围',[ranges(i,C,co) for i in [49,50]],[[25,31]]*2,[49,50]);ck('两底孔轴向',[p(i)[3:6] for i in [49,50]],[C]*2,[49,50])
threads=[f for f in features if f['type']=='CosmeticThread'];ck('装饰螺纹数',len(threads),2);ck('螺纹公称直径',[f['Diameter']*1000 for f in threads],[6,6]);ck('螺纹标注',[f['ThreadCallout'] for f in threads],['M6x1 THRU']*2);ck('螺纹通孔定义',[f['EndCondition'] for f in threads],[2,2]);ck('螺纹长度',[f['BlindDepth']*1000 for f in threads],[6,6])
diam('正面凸台 Φ24',[51],G['outer_diameter']);diam('正面孔 Φ12',[2],G['bore_diameter']);ck('正面孔中心高',[xyz(i)[1] for i in [51,2]],[G['center_height']]*2,[51,2]);ck('正面端面距主管轴 32',plane(52,Z),G['outer_face_to_main_axis'],[52]);ck('正面凸台与孔共轴',[xyz(i)[:2] for i in [51,2]],[[0,20]]*2,[51,2]);ck('正面凸台轴向',[p(i)[3:6] for i in [51,2]],[Z]*2,[51,2])
fillets=[f for f in features if f['type']=='Fillet'];ck('两组铸造过渡特征 R3',[f['DefaultRadius']*1000 for f in fillets],[3,3]);ck('可解析铸造过渡面的 R3',[p(i)[7]*1000 for i in [56,57,61,62,64,68]],[3]*6,[56,57,61,62,64,68])
ck('单实体',m['body_count'],s['verification']['required_body_count'])
def axis_distance(a,b,axis):
 delta=sub(a,b);return norm(sub(delta,mul(axis,dot(delta,axis))))
ck('B 六段 R5 与主体圆弧相切',[axis_distance(xyz(i),back,U) for i in [22,24,26,28,30,32]],[T['body_diameter']/2+T['transition_radius']]*6,[22,24,26,28,30,32])
ck('B 六段 R5 与耳圆相切',[min(axis_distance(xyz(i),xyz(j),U) for j in [25,29,33]) for i in [22,24,26,28,30,32]],[T['lug_radius']+T['transition_radius']]*6,[22,24,26,28,30,32,25,29,33])
def distance_plane(center,i):return abs(dot(p(i)[:3],sub(center,[x*1000 for x in p(i)[3:6]])))
ck('C 四斜边与 R12 相切',[distance_plane(xyz(41),i) for i in [40,42,44,46]],[12]*4,[41,40,42,44,46])
ck('C 四斜边与 R6 相切',[distance_plane(xyz(j),i) for i,j in [(40,39),(46,39),(42,43),(44,43)]],[6]*4,[40,46,42,44,39,43])
report={'status':'MEASUREMENTS_PASS_PENDING_VISUAL_REVIEW' if all(r['status']=='PASS' for r in rows) else 'DRAWING_MATCH_FAIL','model_sha256':m['model_sha256'],'contract_sha256':hashlib.sha256(SPEC.read_bytes()).hexdigest(),'checks':rows,'numeric_tolerance_mm':tol,'scope':'已确认合同与图4-36的名义几何；M6 使用底孔和装饰螺纹表达，非实体牙型。'}
(OUT/'checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8');print(json.dumps({'status':report['status'],'checks':len(rows),'failed':[r for r in rows if r['status']!='PASS']},ensure_ascii=False))
