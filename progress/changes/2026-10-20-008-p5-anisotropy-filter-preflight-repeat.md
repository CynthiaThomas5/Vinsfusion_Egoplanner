# P5 anisotropy-filter 非零目标前置门复测（#208–#209）

对话摘要：[2026-10-20-008](../../collaboration/dialogues/2026-10-20-008-p5-anisotropy-filter-preflight-repeat.md)。轻量证据：[前置门复测报告](../evidence/p5-vins-anisotropy-filter-horizontal-preflight-20261020-208-209.json)。

## 变更

- 复用 #207 编译出的 VINS binary 与显式 opt-in 0.01 feature filter，分别以 ROS domain 226、227 运行 #208/#209；目标配置为相对横移 0.30 m、yaw +30°，质量与 PX4 安全门保持原值。
- 每轮新建自维护 ROS overlay、独立 Gazebo partition、epoch 与 PX4 SITL log。修正 run-local ULog 分析器的 run_id 和结果解释，避免把 #206 的旧 landing 文案带入当前报告。

## 结果

- #208 的完整 preconditions 曾为 true，但 5 秒稳定窗口未通过；#209 的完整 preconditions 未满足。定位分别在仿真 stamp 11.652 s 和 16.428 s 以 `telemetry_stale` 锁定，最后有效源戳为 11.620 s 和 16.072 s。两个 epoch 均保持 locked，不自动恢复。
- 独立 flight harness 在锁定后仍收到 VINS estimator telemetry，最后记录分别到 49.336 s 与 54.420 s；这说明 VINS observer 的收包与 localization adapter 的 freshness 状态不一致，但尚不能区分 publisher 间隙、DDS交付还是订阅回调问题。
- 两轮均没有 TAKEOFF、arm 或导航 goal；bridge 保持 DISABLED、PX4 保持 disarmed。PX4 ULog 分别为 69.064/72.744 s、0 dropout、GNSS aiding flags 全零，短时观察到 EV aiding；没有 DESCEND/failsafe。

## 验证

- 两轮脚本 `bash -n` 通过，独立 6 包自维护 overlay 构建通过；VINS binary SHA 与 #207 一致。
- `python3 artifacts/runs/p5-px4-vio-ego-anisotropy-filter-20261020-208/analyze_px4_ulog.py` 与 #209 对应命令均重算 ULog 状态；两个报告记录的 PX4 最终状态与原始 ULog transition 一致。
- 无真值输入；没有降低 VINS `normalized_cost=1.0`、localization freshness、PX4 65 ms future tolerance 或更改唯一控制发布者。

## 局限与下一步

两轮均未发目标，不能评价横移或 yaw 表现，也不能把 freshness 锁定归咎于 feature filter。下一步先做只读同步时间线，比较 VINS estimator telemetry、optimized/propagated odometry、`/clock` 与 LocalizationStatus 的源戳、收包间隙和回调时间，再决定是否重试飞行。P5 与 GOAL A–H 状态不变。
