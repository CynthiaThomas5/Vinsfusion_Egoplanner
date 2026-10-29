# 2026-10-27 N10.3/#402 快照源时间覆盖准备

## 本轮改动
- 新增 observer-only snapshot coverage helper，按快照前最后一条已记录的正箱体 ROI cloud source stamp 建 watermark，检查 frame 一致性和 map snapshot source stamp 覆盖。
- 综合校准 observer 首次请求时冻结 watermark；source stamp 落后时，最多等待 5 次，每次相隔 0.25 仿真秒，重复同 identity 的只读快照。
- 快照达到次数上限仍可存档，但 evaluator 将覆盖不足判为 INSUFFICIENT；无运行控制副作用。
- evaluator 将时间覆盖状态带入 occupancy 与 acceptance 离线判断。

## 验证
- 用 #398 归档复算：快照前 2 条正 ROI cloud 的最后时间 128.388 s，快照 source stamp 128.372 s，差 -16 ms；helper 正确返回 waiting_for_fusion/should_retry。
- python3 -m unittest tools.test_n10_snapshot_coverage tools.test_n10_occupancy_snapshot tools.test_n10_acceptance tools.test_n10_sensor_capture：45 项通过。
- runtime-driver bash -n 和临时 pycache 下的 Python syntax compilation 通过。
- #402 SITL 未启动；这项只完成采集和评估准备，不宣称获得 source-covered live snapshot。

## 下一步
N10.3/#403 从 X500/D435i 动力学和 #398 逐 4 ms 状态记录推导或否定可信区间净空界。通过前不把 4 ms 离散 clearance 写成连续通过。
