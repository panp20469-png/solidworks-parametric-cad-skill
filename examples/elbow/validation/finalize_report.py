"""验证证据与模型哈希后汇总报告；未审查的新视图不能自动沿用旧结论。"""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/demo/elbow-validation'
def read(n):return json.loads((OUT/n).read_text('utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
r=read('checks.json');v=read('visual-review.json');b=read('basic-checks.json')
assert sha(ROOT/'docs/demo/elbow.SLDPRT')==r['model_sha256']==v['model_sha256']
assert len(r['checks'])==63 and all(x['status']=='PASS' for x in r['checks'])
assert b['rebuild']['rebuilt'] and b['geometry']['errors']==0
assert {x['view'] for x in v['views']}=={'front','top','right','isometric','B','C','front_section','AA','boss_section'}
for x in v['views']:assert x['status']=='PASS' and sha(OUT/(x['view']+'.png'))==x['sha256']
assert len({x['sha256'] for x in v['views']})==9
r.update(status='DRAWING_MATCH_PASS',date=v['date'],method='实体与特征自动读回 + AI 对原图和九个实际 SW 视图进行核对',basic_checks=b,visual_review=v,source_drawing_sha256=sha(ROOT/'docs/demo/source-drawing.png'))
(OUT/'report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n','utf-8')
lines=['# 图 4-36 弯头图纸一致性验收','', '**结果：`DRAWING_MATCH_PASS`（2026-09-30，名义几何范围）。**','',
 '对已公开的 elbow.SLDPRT 只读检查，63 项尺寸、方向、位置、孔贯通范围、螺纹定义及相切检查通过；九个 SW 视图经 AI 对照原图通过。模型未重建、未修改。', '',
 '模型 SHA256：`'+r['model_sha256']+'`。','',
 '[机器可读报告](report.json) · [原始实体测量](measurements.json) · [特征读回](features.json) · [取图方向及 AI 对照记录](visual-review.json)','',
 '## 范围与图纸项目覆盖','',
 '- 底座：60×60、厚 10、R10、四孔 Φ8 和 40×40 孔距。',
 '- 主管：Φ40/Φ30、R35、40/80 高度及 135° 上段方向、内外同轴和上下贯通。',
 '- B 端：厚 10、主体 Φ56、三孔 Φ8、120° 分布、R10 耳和 R5 过渡；轮廓按现有已确认合同核对。',
 '- 侧支管与 C 端：轴高 50、合同确认的轴向和位置、25+6 尺寸链、Φ20/Φ12、R12/R6、两孔间距 32。',
 '- 正面凸台：Φ24/Φ12、中心高 20、端面距主管轴 32，并由 A-A 和纵剖证明内部连通。',
 '- 2×M6 通孔：实际 Φ5 底孔 + M6x1 THRU 装饰螺纹，长度 6；不是实体螺旋牙型。',
 '- 未注铸造过渡：两组圆角特征读回 R3，位于图示连接部位，在 R3～5 范围内；结合实体可解析圆角面及视图核对。',
 '- Ra6.3、HT200、时效处理及不允许气孔/砂眼/裂纹属于材料或制造要求，本次不以 CAD 几何证明这些要求已实现。比例、数量和标题属于图纸元数据。','',
 '数值对比阈值为 0.001 mm，角度检查阈值 0.001°；这是计算复核阈值，不是图纸制造公差。侧支管轴向和上法兰轮廓按仓库中已确认合同解释，未为本次验收修改合同。结论仅适用于此模型哈希，不代表任意工程图的通用自动验收或跨机器运行。','',
 '## 数值核验','', '| 编号 | 项目 | 期望 | 实测 | 结果 |','|---|---|---|---|---|']
def fmt(x):
 if isinstance(x,list):return '['+', '.join(fmt(y) for y in x)+']'
 return f'{x:.6g}' if isinstance(x,(int,float)) else str(x)
for x in r['checks']:lines.append(f"| {x['id']} | {x['label']} | {fmt(x['expected'])} | {fmt(x['actual'])} | {x['status']} |")
lines+=['','## 视图证据','', '普通视图及 B/C 端视在启用剖切之前采集。主剖 Z=0，A-A 为 Y=20，凸台纵剖为 X=0；红色为剖面封盖。原图半剖和局部视图通过全剖与普通视图组合核对。所有截图由 SW 生成，只做像素完全一致的无损 PNG 编码。','']
for x in v['views']:lines += [x['note'],'',f"![{x['view']}]({x['view']}.png)",'']
lines+=['## 复核方式','', '在仓库根目录执行，可重算已发布测量快照并核对模型、截图和审查记录哈希：','', '```powershell','python examples/elbow/validation/check_measurements.py','python examples/elbow/validation/finalize_report.py','```','',
 '重新采集时先在现有 SW 中打开并激活 docs/demo/elbow.SLDPRT，运行 measure_model.py 和 inspect_details.py。这些脚本只读取实体和特征，后者会切换端视显示。面编号只适用于本模型快照；变更模型后必须重新核对面归属及截图，不得自动套用旧的视图审查。', '',
 '本次使用 Python/COM 独立测量、现场 MCP 取标准视图和剖面、AI 进行视觉对照。原始建模仍是此前记录的 Python/COM 两次从零运行，本次没有重跑建模或验证 MCP 完整建模链。']
(OUT/'report.md').write_text('\n'.join(lines)+'\n','utf-8')
(OUT/'validation.json').write_text(json.dumps({'case':'elbow_436','drawing_match':r['status'],'date':r['date'],'checks':63,'reviewed_views':9,'body_count':1,'geometry_errors':0,'model_sha256':r['model_sha256'],'report':'report.md','method':r['method'],'scope':r['scope']},ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps({'status':r['status'],'checks':63,'views':9,'model_sha256':r['model_sha256']}))
