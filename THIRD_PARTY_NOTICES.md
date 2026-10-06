# 第三方来源

`examples/elbow/external_sources/Solidworks-MCP-Server/sw_client.py` 基于 https://github.com/Eduardof0nt/Solidworks-MCP-Server 的本地修改版，原作者 Eduardo Font Cruz，上游采用 MIT 许可证，完整许可文本保留在同目录 `LICENSE`。

本地修改涉及 SolidWorks COM 调用、特征操作及状态检查。此处包含经过案例使用的客户端快照，不代表原作者提供或验证了本项目全部功能。上游精确提交号未记录，不声称对应某个上游发布版本。

Python 与 pywin32 通过环境依赖获取，不随本仓库分发。SolidWorks 商标和软件归其各自权利人所有。

## 案例输入图纸

`docs/demo/source-drawing.png` 为维护者提供的“图 4-36 弯头”工程图。原教材名称、作者和公开再分发授权尚未核实，不声称图纸由本项目原创；根目录 MIT 许可证不涵盖这张第三方图纸。展示来源说明不等于取得原权利人的许可。

`docs/demo/elbow-demo.mp4` 与 `docs/demo/elbow.SLDPRT` 为本案例的运行演示和生成模型，供对照检查，不代表已完成全尺寸与剖面验收。

## 阀体学习图

`docs/demo/valve_ljt06_06/source-drawing.jpg` 为维护者提供的“阀体 LJT06.06”工程图，图框标有“合肥工业大学”。该标识不等于已经核实作者或版权归属；原始出版物及再分发授权未核实。图纸非项目原创，不纳入根目录MIT许可。模型和截图为本次SolidWorks自动化任务生成，完整验收边界见案例说明。
