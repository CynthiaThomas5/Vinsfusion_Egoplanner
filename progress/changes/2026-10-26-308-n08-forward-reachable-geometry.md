# #308：将 N08 单向走廊改为机体形状可达集查询

对话摘要：[2026-10-26 #308](../../collaboration/dialogues/2026-10-26-308-n08-forward-reachable-geometry.md)

## 修改

- `tools/n08_trial_gate.py` 用 `vehicle_envelope.json` 锁定的 X500/D435i SDF 碰撞件，按航向扫掠 AABB 上界检查单向目标和 caller-cancel 停车走廊；完整计入原空间误差、跟踪、侧／垂管道、初始回摆、前向偏置、连续采样和起／终保持。unknown、occupied、越界继续拒绝。
- 由既有 N08 #294 记录计算 PX4 航向相对目标的最大偏差0.015545rad，固定航向 trial 的候选几何范围选用±0.019rad。该观测来自旧运行版本；B 样条 yaw 与实时 VINS yaw 运行时都守同一范围，#309 会验证新版本表现；原配置目标容差、速度、tracking和地图门限不变。
- `tools/run_n08_braking_trial.py` 普通 `single_goal` 使用前向可达集；landing metadata 表示在目的地点落地，返航仅由独立 `round_trip` 第二段命令触发。
- 新增可复算离线审计 `tools/diagnostics/audit_n08_forward_reachable_geometry.py` 和 unknown／occupied／端点保持／固定航向回归。

## 验证

- 对 #305 原始地图离线复算：0.6m目标25查询、0.5m取消走廊21查询，起／终保持均 free；扫掠／保持无 unknown、occupied；中心偏移最大0.250778m，上限0.262500m。详见[证据报告](../evidence/n08-forward-reachable-geometry-replay-20261026-308.md)及其 JSON。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_n08_trial_gate`：28项通过。
- `bash tools/project.sh test`：374项单测和 navigation adapter integration 全通过。
- 修改为纯 Python runtime，无 ROS 包或 C++ 算法修改，不需要 colcon build。新版本 SITL 与运动证据尚未产生。

## 未完成与下一步

N08 仍 `in_progress`。离线 replay 不能替代 fresh 同 run N05、实时 N08 准入、caller-cancel 停止测量或三次同版本单目标 cold start。下一子项 #309 用已通过 N05 入口的侧视剖面做 fresh SITL；准入拒绝时不提交目标或解锁。
