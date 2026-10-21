# P5 raw VINS odometry 与 EGO mapping boundary 复测 #221–#224

日期：2026-10-20

## 任务摘要

- 延续 #220 的横移复测，先在 #221 采集 raw VINS optimized odometry，区分源发布与定位适配器失效。
- 根据 #221 的 EGO 深度超时，在 #224 增加原始/转发深度、depth-health、EGO 位姿、mapping status 与占据时间戳的只读观察器。
- 保持 #192 的 0.30 m/+30°目标、run-local 0008 filter=0.01、定位/PX4健康门和唯一 PX4 控制发布者；不接真值、不改阈值或 PX4 参数。

## 已确认

- #221 raw VINS odometry 连续到 source stamp 73.592 s，定位状态 1110/1110 有效；目标仍因 EGO 内部 depth/odometry timeout 后 `goal_timeout`，安全落地。
- #222 的 ROS domain 233 被 DDS 端口映射拒绝，未进入导航运行；随后改用合法 domain 和新 Gazebo partition。
- #223 的定位适配器在 `telemetry_stale` 后失效，raw VINS odometry 仍继续记录到 75.904 s，VINS telemetry 到 50.228 s；目标未派发。mapping observer 首次初始化失败，修复后晚启也未能写出 trace。
- #224 从启动前挂载修正后的 observer。原始深度最大 source gap 132 ms、适配器转发状态继续增长，depth-health 一直 READY，mapping occupancy 最大 source gap 84 ms。EGO timeout 日志中的内部 depth/pose sync 源戳在输入流继续时停滞，支持 EGO 内部消息同步/回调交付边界的推断，但不证明根因。
- #224 目标随后因 `accel_bias_norm=0.150853 m/s²` 越过既有安全门而中止，车辆落地并解除武装；ULog 记录 AUTO_LAND 和触地前的 DESCEND/failsafe。P5 未通过。

## 决定与待办

- #224 的额外 ROS 图像/点云订阅可能扰动调度，当前观测按诊断证据处理。
- 下一步使用保留 P4 action 集成的 EGO build，并启用既有 patch 0015 的 message_filters receipt/lost 计数，避免额外高带宽图像订阅；继续保持所有健康门、PX4 参数和真值隔离不变。
- GOAL A–H 与 P5 均未完成。
