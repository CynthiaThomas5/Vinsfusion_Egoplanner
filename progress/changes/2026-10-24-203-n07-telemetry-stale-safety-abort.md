# #203 变更记录：N07 遥测 stale 安全中止

## 范围

Goal 完成模式，用户指定 N07。子任务 N07.49 #203：固定运行身份和门限，做新的独立 cold start。仅增加 run-local 只读图观察器副本和运行证据；未修改源码、配置、控制或定位门限。

## 结果

- N05 支架路线 12/12，summary 14/14；post-release/current-area fresh online/offline gates 通过，PX4 boot audit 通过。
- fixture helper 报 `localization changed or became invalid during physical scan`，原样保留；支架 detached、removed、场景缺失且落地。
- flight preconditions 通过并短暂进入 ACTIVE。PX4 `attitude/local_position/land_detected/vehicle_status` 来源时戳分别领先 `/clock` 196/196/180/128 ms，超过固定 65 ms future allowance。bridge 触发 `telemetry_stale` 并安全降落；导航 goal 未发送，悬停仅 0.164 仿真秒，结果 FAIL，连续数为 0/3。
- 图检查确认唯一 bridge 控制发布者与无真值；未取得 airborne graph snapshot。独立 hover evaluator 未运行。原始 ULog 已保存，但 `tools/debug_truth/analyze_n07_ulog.py` 因固定镜像缺少 `pyulog` 而未能解析。
- 独立 postflight safety readback 13/13；`bash tools/project.sh stop n07-20261024-203-01` exit 0，容器 `exited 0`，活动项目容器 0。

## 验证

- `N07_KEEP_SIM=1 bash /tmp/n07-192-n05-runner.sh n07-20261024-203-01 wall_box_column n06_full_airframe_retreat_240_oblique_separated_return`：N05 route 12/12、summary 14/14；fresh post-release/current-area gates 通过。
- 固定 no-goal hover runner：结果 `SAFETY_ABORT/telemetry_stale`，`action_goal_sent=false`，`hover_duration_sim_s=0.164`，最终 landed/disarmed。
- ROS 只读 graph audit：control-owner reconciliation 与 no-truth 检查通过；`airborne_snapshot_captured=false`。
- 独立 ROS/PX4/Gazebo postflight readback 与 clean stop：13/13；容器退出码 0，活动项目容器数 0。
- 固定镜像初次运行 ULog analyzer 时缺少 `pyulog`；随后在 `/tmp` 隔离安装 pyulog 1.2.4 并重跑，EV/no-GNSS 与最终状态检查 PASS；没有更改 SITL 镜像或仓库依赖。
- 本记录写回后运行 `python3 tools/project_status.py` 与 `git diff --check`。

## 限制与下一步

遥测时间戳领先 `/clock` 是本次安全中止的直接原因；领先来源未定位。时钟同步样本为空、DDS 同步未启用，但不足以确定根因。没有 30 秒悬停、独立误差 evaluator 或 airborne graph snapshot 证据，因此 N07 未通过。继续 #204，固定条件与门限不变。详见[N07 #203 报告](../evidence/n07-telemetry-stale-20261024-203.md)与[对话摘要](../../collaboration/dialogues/2026-10-24-203-n07-telemetry-stale-safety-abort.md)。
