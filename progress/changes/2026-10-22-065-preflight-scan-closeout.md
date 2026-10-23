# #065 未武装整机扫描收尾

续测对话：[067](../../collaboration/dialogues/2026-10-22-067-server-continuation.md)。本轮只收尾已有coverage运行，不重新扫描、不解锁。

读取fixture-result/trace及probe源码：成功路径在脱离后请求Gazebo移除支架，未确认移除会抛错。续测用实际`gz model --list`确认支架模型不存在；`ros2 topic echo --once /fmu/out/vehicle_status_v1 ... --field arming_state`返回1。随后`bash tools/project.sh stop flight-safety-20261022-065-coverage-01`退出0。无关容器保留。

按交接运行原capture_grid.py，保存map-after-scan/raw-grid.npz/json；此为扫描完成后一段时间、649.652仿真秒的快照，不是刚脱离瞬间。free39155／occupied1952／unknown9558893。SciPy EDT找到中心[-0.25,3.35,0.6]；进一步枚举与0.5m球相交的823个体素，全部raw free。仅说明该快照至少存在一处可容球区域，不能推断原点起飞、全路径或降落安全。

1381个solve帧覆盖201.368仿真秒，q范围0.145775–0.852622，无分组记录；不能说明先验不增长或证明精确定位。未伪造flight.json，未将关节数据作为高精度真值。固定支架不是默认启动／实机流程。

原始文件：artifacts/runs/flight-safety-20261022-065-coverage-01。轻量[证据和输入哈希](../evidence/preflight-scan-20261022-065.json)。后续不再扩展扫描，优先VINS诊断；完整飞行条件未通过，阶段不升级。
