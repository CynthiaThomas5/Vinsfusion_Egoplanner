#272：N05 支架扫描健康门提前拒绝，未测试起飞观察器假设

## 试验前提

本轮使用新 epoch `98ce8945616f4f7082a393151d375b43` 和正确低速 planner 配置 `config/components/mapping/n08_low_speed_trial.json`（0.10 m/s、0.25 m/s²）。初始 raw-map N05 检查因 `ground_plane_insufficient_raw_occupied_voxels` 拒绝，在线与同图离线一致；按既有流程启动未武装支架扫描。

## 扫描结果

`n08_far_small_pitch_view` 在第 10/15 阶段因 `localization changed or became invalid during physical scan` 结束。最后状态为 `accel_bias_norm_exceeded`，normalized cost 0.572；不触发的是 cost 门，而是加速度 bias 范数越过既有 0.15 m/s² 上限。原始 VINS 记录最大 bias 为 0.155220 m/s²，首次越限在 source stamp 373300000000 ns（0.150122 m/s²）；该帧仍有 161 stereo features、134 long tracks 且 solver usable。健康阈值未改。

扫描记录确认支架 detach、Gazebo remove service acknowledged、模型列表中已不存在夹具；扫描器最终 landed=true。没有 `n05-prescan-ready.json`，因此没有 post-release/current-area admission、preflight、Offboard enable、arming、takeoff 或 EGO goal。N08 runner 在目标假设生效点之前未启动，不能据此判断关闭 PointCloud2 observer 是否缩短定位状态回执空窗。

## 安全末态

停止前直接 ROS 读回：bridge `DISABLED`、`control_enabled=false`、`armed=false`、`landed=true`；PX4 `arming_state=1`、`failsafe=false`；LandDetector `landed=true`、`ground_contact=true`、`at_rest=true`。随后 `bash tools/project.sh stop n08-20261025-272-observer-pre-enable` 退出 0，容器 `exited`、无活动项目仿真。读回原文摘要见 [`final-safety-readback.json`](../../artifacts/runs/n08-20261025-272-observer-pre-enable/final-safety-readback.json)。

## 下一步

#271 使用同一 N05 profile 完成 15/15 并通过释放后准入，但保留泛化状态警告；#272 在同一 profile 的另一个 fresh epoch 中于第10阶段越过 bias 界。只做一次独立冷启动复现，以判断这次是否为 epoch 相关的扫描健康波动。若 #273 再次于返回平移越过同一 bias 门，停止重复 N05 扫描并从源数据检查该运动段；若 N05 通过，则在同一 run 中继续 observer 起飞验证。

结构化报告：[`n08-observer-prerequisite-refusal-20261025-272.json`](n08-observer-prerequisite-refusal-20261025-272.json)。原始运行目录：`artifacts/runs/n08-20261025-272-observer-pre-enable/`。
