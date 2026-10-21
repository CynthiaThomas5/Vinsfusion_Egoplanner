# GOAL C pitch 后真实 3D 目标与快照门诊断 #344

## 结果

在独立 ROS domain 中，按 `/navigation/ego_goal` 发送 epoch 绑定的 `NavigationCommand`，目标为 `[0.25, -0.15, 0.4]`。同 epoch/map_id 的 pitch 前后 plan_env 快照显示目标 voxel `[122,118,5]` 从 unknown 变成 free 且未膨胀；已知体素从 8,034 增至 25,341。

EGO 收到匹配 goal_id/epoch 的目标候选 B-spline，随后记录 depth loss 并输出 emergency-stop spline。两条样条各发起15次快照请求，但都没有接受的规划时刻快照：总计28次因 `depth_pose_gate_closed` 拒绝，2次以 `no_fresh_fused_depth` 结束。EGO depth/pose 同步计数停在932；最后同步时间为35.859 s，首次 timeout 在36.268 s，跨过配置的0.4 s freshness门。MapStatus和定位适配器仍为ready，不能代表EGO独立 reader 收到新鲜配对输入。

本轮不对样条做占据、碰撞或机体净空分类，不作为 GOAL C 验收。无 controller、trajectory server、PX4、真值输入或控制话题；没有执行轨迹，也没有修改canonical或vendor源码。复用的 EGO binary 和实验补丁0033仅在run-local overlay中。

## 验证

- `run-manifest.json` 和轻量 evidence JSON 解析通过，evidence 中的 manifest SHA-256 与归档一致。
- 独立 pitch 前后快照报告确认 epoch/map_id、目标体素状态和相机视锥观测记录；planner gate 统计保留了两条样条各15次请求的拒绝计数。
- 本轮无源码改动；结构检查将运行 `python3 tools/project_status.py`，并运行 `git diff --check`。

证据：[轻量报告](../evidence/p2-ego-observed-voxel-target-planner-probe-20261021-344.json)，原始运行文件和run manifest位于 `artifacts/runs/p2-ego-observed-voxel-target-planner-probe-20261021-344/`。对话摘要：[2026-10-21-011](../../collaboration/dialogues/2026-10-21-011-p2-ego-observed-voxel-target-snapshot-gate.md)。

## 下一步

对齐EGO depth/camera-pose reader实际接收记录、QoS和同步器时间戳与adapter输出；保持0.4 s freshness门不变，只在样条时刻可读快照恢复后继续第二布局和路径检查。unknown继续fail-closed；完整 swept-volume 与机体安全视角动作合同通过前不进入 PX4 动作。
