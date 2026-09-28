# 案例二：109 双耳支架

这是与弯头不同的第二个工程图建模案例。模型已生成并保存；基础检查通过，完整图纸符合性仍待人工验收。

![实际模型](demo/drawing109/model.jpg)

## 素材

- [SolidWorks 原生零件](demo/drawing109/drawing109.SLDPRT)
- [自动建模全过程录像（MP4，2 倍速）](demo/drawing109/automated-build-2x.mp4)：约 56 秒；从空白零件到完成 12 组特征并保存，保留全过程，未剪掉失败片段（本次无失败）。
- [完整运行日志](demo/drawing109/replay-log.json)、[录制信息](demo/drawing109/recording.json)
- [建模入口](../examples/drawing109/build.py)、[尺寸合同](../examples/drawing109/contract.json)、[读图记录](../examples/drawing109/gate.md)
- [基础验证摘要](demo/drawing109/validation.json)

## 输入图纸

![输入二维图](demo/drawing109/source-drawing.jpg)

输入为维护者提供的编号 109 工程图，图框包含 studycadcam 标识，发布图片已替换为维护者提供的干净图纸，去除手机界面，保留原来源标识。图纸非本项目原创，不纳入项目 MIT 许可；未核实其公开再分发授权。

## 建模与恢复

主要尺寸包括总宽 150 mm、底板厚 10 mm、中心凸台外径 50 mm 与通孔 32 mm，以及两个直径 20 mm 的下耳孔。完整尺寸及基准关系见读图记录。

首次建模曾修复首次保存后的文档名称检查及双向对称拉伸参数。最后的 R6 选边得到四条候选边；测量确认其中两条为 66 mm 腹板根部，另两条约 7.30 mm 为后槽口边。因共享合并平面，仅靠坐标与相邻面包围盒筛选不足。最终按中央底面与腹板内面的相邻关系以及边界范围选择，完成 R6。

## 验证与限制

- 实体数：1；重建：通过；几何错误：0。
- 圆角特征实际读回半径：6.0 mm。
- 本次为 Python/COM 建模，不是 MCP 全链路验证。
- `AWAITING_USER_REVIEW`：完整尺寸与剖面对照尚未自动验收。
- 修复已纳入入口；修正后公开案例脚本完整从零重放 `PASS`，12 组特征一次运行全部通过，耗时 110.69 秒。
- 公开副本已在原工作站实际运行；录制包装器仅增加窗口捕获、视图刷新及阶段短暂停顿，不替换几何算法。尚未在另一台电脑验证。

## 运行入口

按仓库首页安装依赖，手动打开 SolidWorks，然后在仓库根目录执行：

```powershell
.\.venv\Scripts\python.exe examples/drawing109/build.py
```

脚本读取固定案例合同，不直接解析图片。复用仓库内弯头案例的平面草图与 COM 封装，因此需保留完整 `examples` 目录结构。结果 `drawing109_generated.SLDPRT` 和恢复状态写入 `examples/drawing109/output/`。已有恢复状态时须保持该案例模型为活动文档；不要用它操作其他零件。
