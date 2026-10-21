# P5 run-local 各向异性 filter 横移对照 #210–#213

对话摘要：[2026-10-20-009](../../collaboration/dialogues/2026-10-20-009-p5-anisotropy-filter-horizontal-paired-runs.md)。轻量证据：[无过滤对照 #210](../evidence/p5-vins-anisotropy-filter-unfiltered-horizontal-control-20261020-210.json)、[0.01 过滤 #211](../evidence/p5-vins-anisotropy-filter-010-horizontal-paired-20261020-211.json)、[0.001 过滤 #212](../evidence/p5-vins-anisotropy-filter-001-horizontal-20261020-212.json)、[0.0025 过滤 #213](../evidence/p5-vins-anisotropy-filter-0025-horizontal-20261020-213.json)。

## 变更

- 归档 #210 无过滤控制，以及复用 #207 VINS binary 的 run-local 阈值 0.01、0.001、0.0025 三轮对照。四轮使用 ROS domain 228、独立 Gazebo partition/epoch、相同 0.30 m 横移/+30° yaw 目标与现有 quality/PX4 gates。
- 为每轮生成 hash-indexed evidence JSON，纳入原始 flight report、PX4 ULog 时间线、图像/residual 对照、来源清单及运行产物 SHA-256；更新 evidence README、CURRENT、README、milestone/checklist evidence 引用。没有修改 canonical VINS、sources.json、定位质量门、PX4 参数或控制发布路径。

## 结果

- 四轮均通过 PX4 遥测和定位稳定前置门，观察到起飞并派发目标；没有一轮完成目标。
- #210 无过滤时 normalized_cost=1.2530。790 个视觉 blocks 中34个大于1.5 px，全部在拟合强边缘1 px内，tensor ratio 中位0.00156；该组贡献视觉 Huber cost 的99.36%。
- #211 阈值0.01的残差样本有756个 blocks、没有 >1.5 px block，视觉 Huber cost 26.91；动作却先因 `accel_bias_norm_exceeded` 中止。首次 invalid 时 reported normalized_cost=0.4442，之后残差样本的 normalized_cost=1.0027。报告没有包含 accel bias 数值本身，无法据此确认 filter 与 bias gate 的因果关系。
- #212 阈值0.001仍有40个 >1.5 px blocks，其局部 tensor ratio P90=0.002258，视觉 Huber cost占比99.24%；normalized_cost=1.03525中止。
- #213 阈值0.0025仍有21个 >1.5 px blocks；局部 tensor ratio 最小0.002223、P10/P90为0.003110/0.006399，其中1个低于阈值但仍出现在 residual factor rows 中，20个不低于阈值。该过滤器作用于当前左图候选，而残差行跨历史帧与双目侧，不能把行级 ratio 当作候选入选记录；高残差组贡献视觉 Huber cost 的97.86%，normalized_cost=1.04248中止。flight harness 最后快照未观测到 disarm；对应 ULog 有触地与 DISARMED transition。
- 四轮 PX4 ULog 均有 EV aiding、无 GNSS aiding、零 dropout，最终记录触地并解除武装；触地后短暂 DESCEND/failsafe。所有报告维持 P5_NOT_PASSED。

## 验证

- 所有 flight harness 结果均为 FAIL，且四轮报告均记录 preconditions、稳定窗口、目标派发、首个无效状态与 ULog。
- 残差图像 join 无缺失，Huber cost 按 observation 重算与 VINS telemetry 相符（最大误差低于 `7e-13`）；四份 ULog 分析均记录 EV aiding、GNSS aiding flags、落地与 disarm transition。
- 对运行脚本执行 `bash -n`，对分析脚本执行 `python3 -m py_compile`；结构检查使用 `python3 tools/project_status.py`。这些检查不代表 P5 通过。
- SITL 使用 `d435i-vins:dev`、PX4 v1.17.0；没有在线真值输入，observer 不发布控制，控制 topics 仍由 `uav_px4_bridge` 独占。

## 局限与下一步

四轮是独立仿真样本，前端跟踪与初始化自然变化；比较不能证明滤波阈值的因果效果或通用性。#211 说明过滤残差并未带来成功导航，#212/#213 也未在当前阈值下移除所有高代价块。停止以单轮代价继续调 threshold；保留 `0008` 为 run-only 诊断，下一步读取现有 estimator/health/轨迹时间线，核对 accel-bias gate 与残差变化的时序，再选择受控干预。P5 与 GOAL A–H 状态不变。
