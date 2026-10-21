# P5 图像边缘与逐特征 residual 独立复测（#205）

对话摘要：[2026-10-20-005](../../collaboration/dialogues/2026-10-20-005-p5-feature-image-correlation-repeat.md)。轻量证据：[图像关联复测报告](../evidence/p5-vins-feature-image-correlation-repeat-20261020-205.json)。

## 变更

- 新建 #205 run-local 目录，复制受控 no-motion SITL harness 与只读 stereo image observer；ROS domain 改为229、Gazebo partition 独立命名，使用新 epoch。
- 保持 canonical VINS、控制、参数和质量门不变，复用 #203 的 feature-residual VINS 安装；离线分析脚本按当前 run ULog 和 telemetry 图像时间自动定位输入。
- 记录越线双目帧、残差 overlay、PX4 ULog timeline、构建日志、图、配置、执行脚本与 SHA-256。

## 结果

- 自维护 overlay 构建6/6；定位与 PX4 freshness 稳定前置门通过，进入 Offboard、解锁、起飞并派发 zero-offset action。
- action 因 `localization_normalized_cost_exceeded` 中止，越线 normalized_cost=1.016411，最终 landed/disarmed；现有门限未变。
- 20个 top residual observations关联7个 feature ID；20/20 残差切向大于法向，15/20 位于拟合图像强边缘1 px内，最大1.948 px，16/20 切向符号相同。#204 则20/20在1 px内、20/20同一切向符号。跨 run 方向主导关系复现，位置与符号有波动。
- PX4 ULog仿真时长28.468秒，无 dropout；EV position/yaw/velocity各23/40样本融合，GNSS aiding各项0/40，battery warning/fault为0。触地后短暂 DESCEND/failsafe，随后 disarm。

## 验证

- #205 `colcon-build.log`：自维护包6/6通过；`package-prefixes.txt` 确认桥接及定位/建图/导航指向本轮安装，VINS指向 #203 隔离诊断安装。
- `python3 artifacts/runs/p5-px4-vio-ego-no-motion-direct-20261020-205/analyze_image_edge_correlation.py`：生成20项残差与高梯度边缘的空间/方向统计。
- `python3 artifacts/runs/p5-px4-vio-ego-no-motion-direct-20261020-205/analyze_px4_ulog.py`：生成EV/GNSS aiding、dropout、land/failsafe timeline。
- SITL只验证本轮图像关联与安全终止；不代表 replay、实机或 P5 导航成功。

## 局限与下一步

当前 feature patch 只序列化排名前20个 observation，因此无法判断其余约840个视觉块的完整空间分布。下一步另加 run-only 诊断补丁序列化全部二维视觉 residual 坐标与向量，保持正常求解、控制和门限不变；以更宽样本检查边缘关系是否同样成立。根因尚未确认，P5和 GOAL A–H 仍未完成。
