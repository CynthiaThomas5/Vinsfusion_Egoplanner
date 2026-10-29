# #305 N08 负Y观察未解除后向前向走廊unknown

- 支架15/15阶段到达负Y侧视并回中；helper最终健康状态warning保留。fixture已移除并landed。after/post-release/current-area N05 online/offline均同identity接受；mission preflight通过。
- N08 runner在goal/enable前因 `trial_corridor_or_home_pad_unknown_or_occupied` 拒绝。home-pad N05通过；start hold有105 unknown，首个方向扫掠查询136 unknown，terminal hold 14 unknown；0.6m capsule首query 217 unknown。
- 同身份map定位unknown中心约x=−1.05m后向薄层，负Y侧视未解决该空间。无action goal、控制／setpoint、飞行或取消制动。独立PX4 readback DISABLED/disarmed/landed/control0，容器Exit(0)。
- `evaluate_odometry.py`对无运动失败记录报source stamps非严格递增；braking evaluator随后因odometry-evaluation文件缺失报错，是未飞行的次生问题，不是制动数据。
- 下一步#306在该run地图缺口依据上添加yaw−π rear-facing视角与分段回中，所有既有门限不变。

证据：[报告](../evidence/n08-negative-y-forward-corridor-unknown-20261026-305.md)、[JSON](../evidence/n08-negative-y-forward-corridor-unknown-20261026-305.json)、[raw run](../../artifacts/runs/n08-cancel-highspeed-prescan-20261026-305/)。
