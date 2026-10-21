# GOAL C 重新观测后 guard 目标的 known-free 栅格连通性 #338

## 结果

对 #337 的同 epoch、同 `map_id` 前后占据快照做离线 6 邻接栅格搜索，并按 D435i SDF 外参从相机位姿反算 VINS IMU 起点。基线时起点格与 #332 guard 目标格均为 unknown，起点例外之外没有可达 known-free 格；pitch 后目标格 `[122,118,5]` 为 free 且 inflation=0。从当前 IMU 起点 `[120,119,1]` 只豁免所在的一个 unknown 格后，存在一条 8 格、7 条边（0.7 m 栅格边长）的路径，其余 7 格全为 known-free 且 inflation=0。

这为下一轮真实 EGO planner-only 请求提供了已观测目标和地图连通性的候选输入。此项是离线栅格连通性，不是 EGO 样条、机体扫掠检查、控制或飞行验收；GOAL C 仍 pending。

## 验证

- `python3 artifacts/runs/p2-camera-pitch-known-free-path-diagnostic-20261021-338/analyze_safe_voxel_path.py`：7 项身份、occupancy、inflation 与连通性检查通过。
- `python3 -m py_compile artifacts/runs/p2-camera-pitch-known-free-path-diagnostic-20261021-338/analyze_safe_voxel_path.py`：通过。
- 独立回读输出与 NPZ：确认 baseline 不连通、pitch 后连通；路径仅起点格为 unknown，其他格均 free 且未膨胀。
- 未启动 ROS/Gazebo/PX4；无真值订阅、导航目标或控制发布。

证据：[轻量报告](../evidence/p2-camera-pitch-known-free-path-20261021-338.json)；脚本、输出和 run manifest 位于 `artifacts/runs/p2-camera-pitch-known-free-path-diagnostic-20261021-338/`。来源 #337 原始快照保持不变。对话摘要：[2026-10-21-009](../../collaboration/dialogues/2026-10-21-009-p2-known-free-voxel-path.md)。

## 下一步

在独立 ROS domain 下对 pitch 后地图发 planner-only 目标，采集实际 EGO 样条与同 stamp 占据快照；unknown 和 inflated 仍必须阻塞。若当前起点 unknown 阻止规划，先审查传感器自体 footprint／起点合同，不全局放宽 unknown；该候选通过后再用唯一 `uav_px4_bridge` 做单独 SITL 动作与机体扫掠净空验证。
