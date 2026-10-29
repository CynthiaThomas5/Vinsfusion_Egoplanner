# #204 变更记录：N07 重置后首次 hover 通过

## 范围

Goal 完成模式，用户指定 N07。子任务 N07.50 #204：以固定镜像、runtime、spawn、layout、support profile、observer set、飞行命令和原门限执行下一次独立 cold start。仅增加 run-local observer copy 与进度／证据文件；未修改源码、配置或阈值。

## 结果

- N05 route 12/12、summary 14/14；post-release/current-area fresh online/offline gate 通过，地图 epoch 与 map id 连续。初始 ground/contact admission 因 `ground_plane_insufficient_raw_occupied_voxels` 拒绝；扫描后准入通过。fixture helper localization health 错误保留，fixture 已拆除并确认落地。
- no-goal hover runner PASS，实际 30.0 仿真秒，`action_goal_sent=false`，tracking 与 telemetry stability 均通过，最终 landed/disarmed。
- ULog analysis PASS（pyulog 1.2.4）：`EKF2_EV_CTRL=15`、`EKF2_GPS_CTRL=0`、`SIM_GZ_EN_ODOM=0`、`UXRCE_DDS_SYNCT=0`；airborne EV position/yaw flags 可见，GNSS flags 均未激活，最终 disarmed/landed。
- 独立 hover evaluator PASS：position error RMS 0.00645 m、P95 0.00827 m、max 0.00911 m；hold drift 由 PX4 local position 和 Gazebo truth 独立报告。图审计 reconciled PASS，3 个快照包含 airborne snapshot，唯一 PX4 控制 publisher 为 bridge，无 ROS truth。
- 独立 postflight readback 全部通过；`bash tools/project.sh stop n07-20261024-204-01` exit 0，容器退出码 0，活动项目容器 0。N07 连续数由 0/3 变为 1/3。

## 验证

- `N07_KEEP_SIM=1 bash /tmp/n07-192-n05-runner.sh n07-20261024-204-01 wall_box_column n06_full_airframe_retreat_240_oblique_separated_return`：N05 route 12/12、summary 14/14。
- current-area `check_n05_entry_live.py` + `evaluate_n05_entry.py`：fresh online/offline gate 接受且匹配；PX4 boot audit 与 preflight readback 11/11 通过。
- `tools/run_vio_no_goal_hover.py` 原固定命令：PASS，30.0 仿真秒，无 goal。
- `PYTHONPATH=/tmp/n07-pyulog-1.2.4 python3 tools/debug_truth/analyze_n07_ulog.py ...`：PASS；隔离分析环境未改动 pinned SITL image。
- `python3 tools/debug_truth/evaluate_n07_hover.py artifacts/runs/n07-20261024-204-01`：PASS。
- `python3 tools/diagnostics/reconcile_n07_ros_graph.py .../ros-graph-audit.json --output .../ros-graph-audit-reconciled.json`：PASS，3 snapshots / airborne snapshot。
- postflight ROS/PX4/Gazebo readback 与 clean stop 全部通过。
- 本记录写回后运行 `python3 tools/project_status.py` 和 `git diff --check`。

## 限制与下一步

这是 #203 失败后的第一项有效通过，只将 N07 streak 提至 1/3；N07 仍未完成。地下不是飞行区域；N05 ground/contact admission 只决定当前已落地状态是否准许起飞。继续 #205，保持全部冻结条件和门限不变。详见[N07 #204 报告](../evidence/n07-no-goal-hover-20261024-204.md)与[对话摘要](../../collaboration/dialogues/2026-10-24-204-n07-first-hover-after-reset.md)。
