# #381 N10.3 raw VINS 速度观测器补齐

- **背景**：#376/#361 的 raw VINS 观测只保存 pose，不保存 `nav_msgs/Odometry.twist.twist.linear`，因此不能评估最终长航段运动中的 VINS 速度误差。
- **源审计**：`src/vendor/vins_fusion/vins/src/utility/visualization.cpp` 将 `estimator.Vs` 写到 raw odometry `twist.linear`；该量用 VINS `WORLD_FRAME_ID` 表达。只读 recorder 现在原样保存 `linear_velocity_world_m_s`，不转发、不发布控制。
- **新增评估器**：`tools/debug_truth/evaluate_n10_vins_velocity.py` 使用单次 scale=1 prestream 固定对齐，把 VINS 速度与 D435i IMU 原点的 Gazebo truth 中心有限差分比较；采用两侧各 0.1 仿真秒的窗口和已有0.04秒真值插值支持限制，报告 goal-motion、post-goal hold、全程三段统计和覆盖，不设置新的验收/运行门限。
- **运行配置**：只新增 N10.3/#381 运行前协议、离线 evaluator 与 run-local recorder 字段；PX4、EGO、world、spawn、goal、速度、碰撞和健康门行为均未改。runtime-contract 更新到 `547082a4538a871dd3c3b9b26c0f6b45369fa18bf1b73a8d93f219ef3e537cce`（666文件）。
- **验证**：两 Python 文件语法编译通过；run-local Bash `bash -n` 通过；冻结的 runtime/protocol/prelaunch/driver/recorder/evaluator/planner/spawn hashes 全部匹配；`python3 tools/project_status.py` 返回 `Structure/design check: PASS`。该结构检查不替代 SITL。
- **SITL 状态**：本记录写入时尚未启动。#381 协议要求只提交一次16 m目标，记录动态箱体和600秒 ACTIVE hold，并在结束后独立确认 landed/disarmed/control-disabled/zero-control。
- **局限**：velocity truth 是0.2仿真秒中心窗口平均值，不是瞬时高频真值；当前只是校准诊断，不构成速度阈值或资格判定。
- 对话摘要：[2026-10-27-381-n10-raw-vins-velocity.md](../../collaboration/dialogues/2026-10-27-381-n10-raw-vins-velocity.md)。
- 协议：[N10.3/#381](../evidence/n10-vins-velocity-full-route-protocol-20261027-381.md)；运行前身份：[prelaunch](../evidence/n10-vins-velocity-calibration-prelaunch-20261027-381.md)。

## #381 SITL结果与分段复算

准备记录写入时 SITL 尚未启动；其后按同一冻结哈希运行一次完整实验。项目容器 preflight 与 official_ego 起飞准入通过，唯一 16 m 目标 action 成功，独立真值同时位置/yaw dwell 为 3.055 wall 秒；600 simulated-second ACTIVE hold 完成。raw VINS 速度真值配对 10,206/10,206，覆盖率 100%，无拒绝样本。

完整航段为 673.596 仿真秒／27.650 m 真值路程。固定对齐 raw VINS 位置 P95/max 为 0.439/0.458 m、yaw 为 6.585/6.869°；10 s RPE 平移 P95 0.0417 m、旋转 P95 0.3005°。goal-motion 速度误差 P95 0.0282 m/s，精确 600 s hold P95 0.0070 m/s。hold 相对目标的独立真值位置误差 P95/max 0.447/0.456 m，目标完成后 226.096 仿真秒首次超过 0.30 m 球，说明长时间绝对漂移与短时 RPE 表现不同。

发现冻结速度评估器的 `post_goal_active_hold` 统计窗延伸到 LANDED（605.352 s），混入约 5.352 s 着陆数据。原报告和输入保持不变；新增 [分段复算器](../../tools/debug_truth/evaluate_n10_full_route_vio_metrics.py) 与 [结果](../../artifacts/runs/n10-20261027-381-vins-velocity-full-route/n10-full-route-vio-segmented-metrics.json)，按准确 hold 与 hold-end-to-LANDED 两段报告，并复用 N01 `_rpe` 计算 1/5/10 s SE(3) 相对误差。复算器还复核与既有 `evaluate_arrival.py` 一致的固定前置对齐、base-to-IMU lever arm 和 wall-time 同时容差驻留；3.055 s 结果相同。

动态箱体创建 ACK 后 0.536 仿真秒出现首条替换样条；替换样条中心线到箱体的采样距离 1.451 m，整体场景采样净空调整下界 0.262 m，箱体单体为 0.839 m。三次 raw 0.25 m 地图查询仍返回 unknown（每次112 unknown／48 free／0 occupied），没有增加整曲线 raw-free 门。零违规接触。独立末态读回 LANDED/disarmed/control-disabled/zero-control，安全停止文件为 true，项目容器由 `tools/project.sh stop` 退出0。

验证：`python3 tools/debug_truth/evaluate_n10_full_route_vio_metrics.py artifacts/runs/n10-20261027-381-vins-velocity-full-route` 退出0；脚本内存语法编译通过。初始构建结构检查 `python3 tools/project_status.py` 为 PASS（仅结构检查）。全部归档、逐输入哈希与局限见 [#381 结果报告](../evidence/n10-vins-velocity-full-route-result-20261027-381.md) 和对应 JSON。

**边界**：本次是单次 PX4 SITL 校准诊断，不是 N10.3 最终标准通过；长航段 raw 速度仅一份全覆盖样本，净空／重规划未重复，样条采样不是连续动力学证明。N10.3 当前下一项为 #382 证据支持矩阵；N10 保持 `in_progress`。
