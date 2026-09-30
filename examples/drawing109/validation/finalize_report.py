"""汇总数值核验及已完成的 AI 视图审查；不把缺少审查的截图自动判为通过。"""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'docs/demo/drawing109/full-validation'
def read(name):return json.loads((OUT/name).read_text('utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
report=read('checks.json');review=read('visual-review.json');basic=read('basic-checks.json')
model=ROOT/'docs/demo/drawing109/drawing109.SLDPRT'
assert sha(model)==report['model_sha256']==review['model_sha256']
assert len(report['checks'])==50 and all(r['status']=='PASS' for r in report['checks'])
assert basic['rebuild']['rebuilt'] and basic['geometry']['errors']==0
assert {r['view'] for r in review['views']}=={'front','top','right','isometric','front_section','top_section'}
for row in review['views']:
 assert row['status']=='PASS' and sha(OUT/(row['view']+'.png'))==row['sha256']
report.update(status='DRAWING_MATCH_PASS',date=review['date'],method='实际实体几何自动测量 + AI 对图纸和六个 SW 视图进行对照',basic_checks=basic,visual_review=review,source_drawing_sha256=sha(ROOT/'docs/demo/drawing109/source-drawing.jpg'),contract_sha256=sha(ROOT/'examples/drawing109/contract.json'))
(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
lines=['# 109 双耳支架图纸一致性验收','', '**结果：`DRAWING_MATCH_PASS`（2026-09-30）。**','',
 '对已公开的原生模型进行只读检查，没有重新建模或修改模型。34 项尺寸和 16 项位置、轴向、贯通、相切、对称及实体数检查通过；六个视图经 AI 对照原图通过。', '',
 '这是固定案例的名义几何验收：数值由 SolidWorks 实体面、边界圆和端点独立读取，数值比较阈值为 0.001 mm（计算核验阈值，不是图纸制造公差）。截图由 SolidWorks 直接输出，仅无损转码为 PNG。材料、未标注制造要求、其他图纸和跨机器运行不在本次验收范围。','',
 '模型 SHA256：`'+report['model_sha256']+'`。','',
 '[机器可读报告](report.json) · [原始实体测量](measurements.json) · [AI 视图审查](visual-review.json) · [取图与方向记录](view_capture_verified.json)','',
 '## 尺寸与关系核验','', '| 编号 | 项目 | 图纸期望（mm；方向/数量除外） | 实测 | 结果 |','|---|---|---|---|---|']
def fmt(v):
 if isinstance(v,list):return '['+', '.join(fmt(x) for x in v)+']'
 return f'{v:.6g}' if isinstance(v,(int,float)) else str(v)
for r in report['checks']:lines.append(f"| {r['id']} | {r['label']} | {fmt(r['expected_mm'])} | {fmt(r['actual_mm'])} | {r['status']} |")
lines+=['','## 视图证据','', '正视剖切位于 Z=0；俯视剖切位于 Y=23，穿过后耳孔轴。原图俯视为局部剖切组合表达，因此同时使用未剖切俯视图核对凸台外圆。红色为 SW 剖面封盖，橙色为原生参考几何标记。','']
for r in review['views']:lines += [r['note'],'',f"![{r['view']}]({r['view']}.png)",'']
lines+=['## 复核方式','', '在仓库根目录运行以下命令，可重算已发布测量快照的 50 项数值检查，并检查视图审查记录和文件哈希：','', '```powershell','python examples/drawing109/validation/check_measurements.py','python examples/drawing109/validation/finalize_report.py','```','', '需要重新采集实体时，先在现有 SW 实例中打开并激活 docs/demo/drawing109/drawing109.SLDPRT，再运行 examples/drawing109/validation/measure_model.py。不要运行建模入口来替代测量。面编号只适用于这个模型快照；新模型需重新确认面归属、拍摄剖面并审查，旧审查记录不能自动沿用。','', '本次数值核验使用 Python/COM，连接、取图及剖面操作使用现场 MCP。它不证明 MCP 完成了原始建模全链路。显示恢复时发现 RemoveSectionView 返回 false，随后关闭本次只读检查文档并重新打开，未保存显示改动；普通视图与剖面图哈希均不同。']
(OUT/'report.md').write_text('\n'.join(lines)+'\n','utf-8')
print(json.dumps({'status':report['status'],'checks':len(report['checks']),'views':len(review['views']),'model_sha256':report['model_sha256']}))
