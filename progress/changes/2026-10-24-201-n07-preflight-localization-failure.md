# #201 变更记录：N07 起飞前 IMU 时间戳超前

## 范围

Goal 完成模式，用户指定 N07。子任务 N07.47 #201：使用冻结配置、支架路线、观察器和原门限完成一次新独立 cold start。仅写入 run-local observer copy 与运行／进度证据；没有修改项目源码、配置、阈值或 N07 验收条件。

## 结果

N05 路线 12/12、summary 14/14、post-release/current-area fresh gates 和 PX4 boot audit 通过。fixture helper 的 localization health 错误保持记录。no-goal runner 在起飞前因 `imu_from_future`/`localization_not_tracking` 失败，没有目标、起飞或 ACTIVE/armed；连续通过数从 1/3 归零为 0/3。直接观测到 IMU 时间戳领先 `/clock` 48ms，超过原 20ms future tolerance；VINS raw odometry、telemetry、depth、clock 仍推进，来源未确定。

## 验证

- `N07_KEEP_SIM=1 bash /tmp/n07-192-n05-runner.sh n07-20261024-201-01 wall_box_column n06_full_airframe_retreat_240_oblique_separated_return`：支持路线 12/12；summary 14/14；helper exit 1 的状态保留；release/current-area online/offline gates 通过。
- `python3 tools/evaluate_n05_entry.py --live-report .../n05-current-area/n05-live-entry-check.json`：offline replay 与 online gate 匹配并接受。
- `tools/audit_px4_boot.py .../n07-20261024-201-01`：PASS。
- `tools/run_vio_no_goal_hover.py ...`：FAIL_PRECONDITION，`vio_bridge_map_preconditions_not_ready`；未发送目标。
- 独立最终 safety readback：11/11 PASS；`bash tools/project.sh stop n07-20261024-201-01`：exit 0，容器 `exited 0`，无活动项目容器。
- `python3 tools/project_status.py` 与 `git diff --check` 在本记录写回后复验。

## 限制与下一步

没有 ACTIVE/armed 图快照、悬停、独立 hover evaluator 或 airborne ULog 资格结果。`health_future_observation` 的源时间领先来源未确认；不得放宽原门限。继续 #202 做新的独立 cold start，记录同一触发是否重现。详细文件哈希见 [N07 #201 报告](../evidence/n07-preflight-localization-failure-20261024-201.md)；任务摘要见 [对话摘要](../../collaboration/dialogues/2026-10-24-201-n07-preflight-localization-failure.md)。
