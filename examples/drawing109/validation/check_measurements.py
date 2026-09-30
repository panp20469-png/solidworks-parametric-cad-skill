"""核验指定模型快照；面编号只对 measurements.json 对应的 SHA256 有效。"""
import json, math, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'docs/demo/drawing109/full-validation'
contract=json.loads((ROOT/'examples/drawing109/contract.json').read_text('utf-8'))
data=json.loads((OUT/'measurements.json').read_text('utf-8'))
F={f['id']:f for f in data['faces']};D=contract['dimensions'];tol=contract['verification']['length_tolerance_mm'];rows=[]
def p(i):return F[i]['params_si']
def xyz(i):return [x*1000 for x in p(i)[:3]]
def r(i):return p(i)[6]*1000
def coord(i,axis):
 assert F[i]['type']=='plane' and abs(abs(p(i)[axis])-1)<1e-8
 return p(i)[axis+3]*1000
def span(i,axis):
 values=[v[axis] for e in F[i]['edges'] for v in (e['start'],e['end']) if v is not None]
 # 完整圆边界没有顶点；沿圆法向测量时，其圆心坐标就是端面位置。
 for e in F[i]['edges']:
  c=e.get('circle_si')
  if c and abs(abs(c[axis+3])-1)<1e-8:values.append(c[axis]*1000)
 return [min(values),max(values)]
def compare(a,b):
 if isinstance(a,(list,tuple)):return len(a)==len(b) and all(compare(x,y) for x,y in zip(a,b))
 return abs(a-b)<=tol
def add(key,label,actual,expected,faces):
 rows.append(dict(id=key,label=label,expected_mm=expected,actual_mm=actual,faces=faces,status='PASS' if compare(actual,expected) else 'FAIL'))
def dim(n,label,actual,faces,count=None):
 key=f'D{n:02}';expected=D[key] if count is None else [D[key]]*count;add(key,label,actual,expected,faces)
dim(1,'后耳总宽',coord(16,0)-coord(24,0),[16,24])
dim(2,'安装孔轴间距',xyz(59)[0]-xyz(58)[0],[58,59])
dim(3,'后壁外宽',coord(37,0)-coord(28,0),[28,37])
dim(4,'后槽宽',coord(18,0)-coord(0,0),[0,18])
dim(5,'后耳厚度',[coord(26,2)-coord(23,2),coord(39,2)-coord(17,2)],[26,23,39,17],2)
dim(6,'后槽深度',coord(20,2)-coord(17,2),[20,17])
dim(7,'中央桥厚',coord(30,2)-coord(20,2),[30,20])
dim(8,'竖孔轴至后边',xyz(55)[2]-coord(17,2),[55,17])
# S 形肩部理论线由两段相切圆弧的公共切点确定，避免把圆角外包框当理论交点。
shoulder_z=xyz(7)[2]+r(7)
dim(9,'耳前面至肩部',shoulder_z-coord(26,2),[7,26])
dim(10,'肩部至前边',coord(10,2)-shoulder_z,[7,10])
dim(11,'翼板宽',coord(14,0)-coord(6,0),[14,6])
dim(12,'前板宽',span(10,0)[1]-span(10,0)[0],[10])
dim(13,'凸台外径',2*r(41),[41])
dim(14,'两安装孔直径',[2*r(i) for i in [58,59]],[58,59],2)
dim(15,'后槽内角 R3',[r(i) for i in [19,21]],[19,21],2)
dim(16,'弯壁内侧 R12',[r(i) for i in [29,36]],[29,36],2)
dim(17,'后壁与翼板局部 R6',[r(i) for i in [5,15,27,38]],[5,15,27,38],4)
dim(18,'凸台旁 R3',[r(i) for i in [31,34]],[31,34],2)
dim(19,'肩部四处 R12',[r(i) for i in [7,8,12,13]],[7,8,12,13],4)
dim(20,'竖孔直径',2*r(55),[55])
dim(21,'凸台总高',coord(42,1)-coord(2,1),[42,2])
dim(22,'后壁总高',coord(40,1)-coord(2,1),[40,2])
dim(23,'两安装孔轴高',[xyz(i)[1]-coord(2,1) for i in [58,59]],[58,59,2],2)
dim(24,'两腹板厚度',[coord(22,0)-coord(9,0),coord(11,0)-coord(1,0)],[22,9,11,1],2)
dim(25,'耳台内间距',coord(54,0)-coord(47,0),[54,47])
dim(26,'耳台外间距',coord(53,0)-coord(48,0),[53,48])
dim(27,'两耳孔直径',[2*r(i) for i in [56,57]],[56,57],2)
dim(28,'两腹板内根 R6',[r(i) for i in [60,61]],[60,61],2)
dim(29,'孔轴至前边',coord(10,2)-xyz(55)[2],[10,55])
def plane_z_at_y0(i):
 a=p(i);return (sum(a[j]*a[j+3] for j in range(3))/a[2])*1000
dim(30,'后斜面延长至板底的理论位置',[-plane_z_at_y0(i) for i in [44,50]],[44,50],2)
dim(31,'底板厚',coord(4,1)-coord(2,1),[4,2])
dim(32,'下耳孔轴至板底',[coord(2,1)-xyz(i)[1] for i in [56,57]],[56,57,2],2)
dim(33,'两下耳外径',[2*r(i) for i in [46,52]],[46,52],2)
dim(34,'腹板后缘 R25',[r(i) for i in [45,51]],[45,51],2)
def rel(key,label,actual,expected,faces):add(key,label,actual,expected,faces)
rel('R01','三组孔轴方向（绝对分量）',[[abs(x) for x in p(i)[3:6]] for i in [55,56,57,58,59]],[[0,1,0],[1,0,0],[1,0,0],[0,0,1],[0,0,1]],[55,56,57,58,59])
rel('R02','凸台与竖孔共轴 XZ',[[xyz(i)[j] for j in [0,2]] for i in [41,55]],[[0,0],[0,0]],[41,55])
rel('R03','下耳圆柱与孔共轴 YZ',[[xyz(i)[j] for j in [1,2]] for i in [46,52,56,57]],[[-D['D32'],0]]*4,[46,52,56,57])
rel('R04','安装孔对称位置', [xyz(i)[:2] for i in [58,59]],[[-D['D02']/2,D['D23']],[D['D02']/2,D['D23']]],[58,59])
rel('R05','竖孔圆柱边界贯穿 Y0 至 Y45',span(55,1),[0,D['D21']],[55])
rel('R06','两安装孔贯穿整个耳厚',[span(i,2) for i in [58,59]],[[-D['D08'],-D['D08']+D['D05']]]*2,[58,59])
rel('R07','耳孔贯穿各耳台且中间分离',[span(i,0) for i in [57,56]],[[-D['D26']/2,-D['D25']/2],[D['D25']/2,D['D26']/2]],[57,56])
rel('R08','内根圆角轴位置',[[xyz(i)[j] for j in [0,1]] for i in [60,61]],[[D['D25']/2+(D['D26']-D['D25'])/4-D['D24']/2-D['D28'],-D['D28']],[-(D['D25']/2+(D['D26']-D['D25'])/4-D['D24']/2-D['D28']),-D['D28']]],[60,61])
# 距离由实际平面方程与圆柱轴计算，用于验证侧面切线关系。
def line_distance(i,center):
 a=p(i);return abs(sum(a[j]*(center[j]-a[j+3]*1000) for j in range(3)))
rel('R09','前后腹板斜面与下耳外圆相切',[line_distance(i,xyz(c)) for i,c in [(43,46),(44,46),(49,52),(50,52)]],[D['D33']/2]*4,[43,44,46,49,50,52])
rel('R10','R25 与板底及后斜面相切',[abs(xyz(45)[1]),line_distance(44,xyz(45)),abs(xyz(51)[1]),line_distance(50,xyz(51))],[D['D34']]*4,[45,44,51,50])
rel('R11','前斜面理论起点',[plane_z_at_y0(i) for i in [43,49]],[D['D29']]*2,[43,49])
rel('R12','肩部双圆弧相切',math.dist(xyz(7),xyz(8)),r(7)+r(8),[7,8])
rel('R13','实体数',data['body_count'],1,[])
rear=D['D08'];ear=rear-D['D05'];slot=rear-D['D06'];bridge=slot-D['D07'];wing=D['D11']/2;wall=D['D03']/2;boss=D['D13']/2
radius_centers={19:[D['D04']/2-D['D15'],-slot-D['D15']],21:[-D['D04']/2+D['D15'],-slot-D['D15']],29:[-wall+D['D16'],-bridge-D['D16']],36:[wall-D['D16'],-bridge-D['D16']],27:[-wall-D['D17'],-ear+D['D17']],38:[wall+D['D17'],-ear+D['D17']],5:[-wing-D['D17'],-ear+D['D17']],15:[wing+D['D17'],-ear+D['D17']],31:[-boss-D['D18'],-bridge+D['D18']],34:[boss+D['D18'],-bridge+D['D18']],7:[-wing+D['D19'],-ear+D['D09']-D['D19']],8:[-D['D12']/2-D['D19'],-ear+D['D09']+D['D19']],12:[D['D12']/2+D['D19'],-ear+D['D09']+D['D19']],13:[wing-D['D19'],-ear+D['D09']-D['D19']]}
rel('R14','各俯视圆角的局部圆心位置',[[xyz(i)[0],xyz(i)[2]] for i in radius_centers],list(radius_centers.values()),list(radius_centers))
rel('R15','俯视圆角轴均平行 Y',[[abs(a) for a in p(i)[3:6]] for i in radius_centers],[[0,1,0]]*len(radius_centers),list(radius_centers))
vertices=[v for f in F.values() for e in f['edges'] for v in [e['start'],e['end']] if v is not None]
mirror_errors=[min(math.dist([-v[0],v[1],v[2]],q) for q in vertices) for v in vertices]
rel('R16','全部边界顶点关于 X0 镜像的最大误差',max(mirror_errors),0,list(F))
views=json.loads((OUT/'view_capture_verified.json').read_text('utf-8'))
for v in views:
 v['sha256']=hashlib.sha256((OUT/(v['spec']['name']+'.png')).read_bytes()).hexdigest()
 v['orientation_check']=json.loads(v['orientation']['structuredContent']['result'])['orientation_verified']
assert len({v['sha256'] for v in views})==len(views),'截图重复：不能用作不同视图证据'
assert all(v['orientation_check'] for v in views)
report={'mode':'full_drawing_match','model_sha256':data['model_sha256'],'tolerance_mm':tol,'scope':'109 号图纸标注的名义几何；不包含未指定制造公差、材料或跨机器建模验证','dimension_rows':34,'checks':rows,'views':views,'status':'MEASUREMENTS_PASS_PENDING_VISUAL_REVIEW' if all(x['status']=='PASS' for x in rows) else 'DRAWING_MATCH_FAIL'}
(OUT/'checks.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),'utf-8')
print(json.dumps({'status':report['status'],'checks':len(rows),'failed':[x for x in rows if x['status']!='PASS']},ensure_ascii=False))
