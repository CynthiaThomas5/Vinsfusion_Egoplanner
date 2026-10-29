# N07 实际 EKF2 融合与无目标悬停

- 用户指令：继续 N07；本轮采用 N07 Goal 完成模式，范围止于 N07 的全部出口。
- 已确认基础：N02、N03、N05、N06 依赖满足；N06 通过 planner 集成及 N05 释放后入口准入，不代表飞行资格。当前运行镜像为固定 `d435i-vins:dev`，`config/runtime.json` 哈希为 `a862e521dd738dba71d960cda95458509336f1e2cd845228b46311fd57928221`。
- N07 出口：每次新鲜 DISARMED N05 当前区域检查后，使用同一源码、参数、模型与镜像完成 3 次独立冷启动；各自无导航目标悬停至少 30 仿真秒，采集独立 VINS/真值误差与保持误差，确认健康／时间映射／控制连续，落地并 DISARMED；ROS graph、PX4 参数及 ULog 证明 EV 融合、无 GNSS／真值辅助和唯一控制发布者。
- 用户授权仅涵盖 PX4 SITL 仿真。Gazebo Transport `/debug_truth/base_odometry` 只供 `tools/debug_truth/record_truth.py` 读取；不启用 ROS 真值适配器，不将真值送入定位、规划或控制。
- 允许变更：N07 只读记录／离线评估工具、为 fresh N05 正向入口所需的 DISARMED 支架观测 profile 与本轮进度记录。禁止放宽门限、改 N06/N08/N09 验收范围、连接实机或推送。
- 本轮子项 N07.1：补足跨进程单调时钟，写出可复算的 hover 误差报告与 ROS graph／ULog 审计，再进行首轮冷启动。尚无 N07 飞行运行结果；先前 #054、#396 不抵扣本次三连。
- 待决问题：无。若首轮触发 fail-closed，先确认安全落地，再根据新增证据决定是否最小修复；任何影响运行的版本变更都使三连从头开始。

## #154-01 准入诊断

- 默认起点 `-8,0,0.3,0,0,0` 的新鲜 N05 在线／离线一致拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`。ground plane 从 110 个 raw occupied voxel 拟合为 z=−0.35m；HOLD 1m 高度 unknown=565、subground exclusion=0。因此拒绝发生在飞行体积，地下体素与 HOLD 拒绝无关。
- coverage 支架诊断保持 DISARMED、无控制／目标；完成静止、升高、+1.2m 平移后，快速 yaw 阶段触发 VINS `accel_bias_norm_exceeded`。安全清理回位、detach 且确认 fixture 已移除；PX4 全程 DISARMED，容器已停止，没有起飞或 N07 飞行证据。
- 为保留默认起点，新增 `n07_default_spawn_oblique_translation_only`：沿用 #146 的 +1.2m 低速观察、+0.45rad 下视和分段实际回程，整个profile无 yaw。完整静态连续余量 1.029m；见 `progress/evidence/n07-support-scan-route-geometry-20261023-154.json`。
- 当前合格 hover 数仍为 0/3。#154-02 的初始 gate 仍拒绝；支架平移保持 Tracking，但开始 pitch 后 normalized cost 升至 1.435091 并锁存。支架已 detach/删除，机体回到默认 −8m 地面近水平姿态，bridge DISABLED、PX4 DISARMED/landed，容器 exit 0；没有扫描后 gate 或起飞。
- 基于该结果，当前 N07 支架 profile 已将 yaw/pitch 固定为 0，保留 +1.2m 平移时长与安全回程。下一次冷启动先确认纯平移全程健康，再看释放后的 N05 五阶段结果；只有准入全通过才做悬停。

## #154-03 纯平移与未知区域定位

- 原默认起点 −8m、当前固定镜像。纯 +1.2m 平移／停留／回程完成 12/12 阶段，trace 中 VINS 持续 valid、epoch/map_id 未变；没有 yaw 或 pitch。fixture runner 在 detach 检查阶段记录 status-change 错误，但实际 detached、删除确认成功；释放后 fresh N05 报告显示 VINS Tracking 且同一身份。
- 初始 gate、扫描后附着 gate、释放后 gate 均在线／离线一致拒绝 TAKEOFF_CONTACT；释放后 HOLD unknown=449、subground exclusion=0。逐格审计显示这 449 个 cell 的中心高度为 0.55–1.25m，raw ground plane 为 −0.35m，全部在地面以上；356 个 cell 的 x<0，位于当前相机 +X 朝向的后侧。纯 +X 只减少 116 个 unknown，没有取得入口。
- 加入 `n07_default_spawn_bidirectional_translation_only` 候选：从 0 后退到 −0.8m，再前进到 +1.2m 并回 0，yaw/pitch 固定0。原场景及扫描时动态加入的 wall/column 几何纳入静态包络审计，最小连续余量 0.389m。profile 工具测试21项通过。
- 当前合格 hover 数仍为 0/3；未解锁。接下来在仍运行的 #154-03 DISARMED 会话里诊断 bidirectional profile 和新鲜释放后 gate；因新增 profile 晚于本次冷启动，该会话不计 N07 资格。若 gate 五阶段通过，再以固定新配置重新冷启动，开始 N07 三连。
