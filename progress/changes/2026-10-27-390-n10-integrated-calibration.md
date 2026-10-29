# #390 N10 综合校准与观测器修复

- 对话摘要：[N10.3 #390 综合校准](../../collaboration/dialogues/2026-10-27-390-n10-integrated-calibration.md)
- 结果报告：[综合校准 #390](../evidence/n10-integrated-calibration-result-20261027-390.md)
- 主运行产物：`artifacts/runs/n10-20261027-390-integrated-calibration/`

## 改动

- 完成 #390：16 m action、60 仿真秒 ACTIVE hold 和最终落地上锁都成功；缺失 truth、资源记录及 raw 查询接受状态使相关离线指标为 `INSUFFICIENT`。
- 修正 Gazebo Odometry protobuf twist 字段访问、resource observer 的 clock QoS 和 SIGINT 清理。
- 新增 N10 occupancy query contract helper；raw sphere 与 official planning point 使用各自服务半径语义，采集完整性校验接受状态、地图身份、半径和中心回显。
- 更新 `config/acceptance.json` 草案的查询说明、N10 map snapshot evaluator 以及相应测试。阈值与任务控制行为未因此改变。

## 验证

- `python3 -m unittest tools.test_n10_map_query_contract tools.test_n10_acceptance tools.test_n10_occupancy_snapshot`：19 passed。
- `PYTHONPYCACHEPREFIX=/tmp/n10-pycache python3 -m py_compile tools/n10_map_query_contract.py tools/diagnostics/query_occupancy_points.py tools/debug_truth/evaluate_n10_occupancy_snapshot.py tools/debug_truth/evaluate_n10_acceptance.py`：通过。
- `bash tools/project.sh test`：455 passed；navigation adapter integration 与 official EGO probe 通过。
- #390 安全收尾读回：LANDED、disarmed、control disabled、control samples 0；`bash tools/project.sh stop n10-20261027-390-integrated-calibration` 返回 0。

N10 保持 `in_progress`。#390 原运行身份及错误报告保留；下一步用单独冻结的 #391 run-local 工具重做综合采集。
