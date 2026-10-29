#265：N05 通过后，N08 watchdog 对控制点包络过度拒绝

## N05 与任务准入

#265 关闭了 N05 扫描期间额外的 localization source timeline observer，其他布局、profile、低速 planner 和健康门保持不变。全机支架路径完成 15/15 阶段；15911 条扫描轨迹样本均为 `TRACKING/valid`，同一 epoch/map_id，normalized cost 峰值 0.61575。扫描器的 `fixture-result.json` 仍报告泛化错误 `localization changed or became invalid during physical scan`，该错误与有效轨迹／后续准入记录不一致，保留为未归因警告。支架已脱离，Gazebo 确认 fixture 模型移除，PX4 全程 DISARMED/landed。

初始 N05 因 ground-plane raw occupied 候选数 0 拒绝；扫描后及支架释放后 online/offline 同图检查均以 `all_entry_phases_known_and_clear` 接受。mission current-area 检查也接受同一 epoch/map_id，快照龄 0.108 s、深度源龄 0.124 s、融合龄 0.036 s（门限0.4 s）。40.000 s 只读 preflight 通过；其中 optimized odometry 最大回执间隔 0.3075 s，1 次超过内部 guard 统计值，作为曲线未开始前的运行特征保留，不归因为后续 watchdog 触发。

低速 planner 配置和 source hash 正确：`n08_low_speed_trial.json`，`max_vel=0.10 m/s`、`max_acc=0.25 m/s²`。fresh same-run 起飞点和前向 0.6 m corridor 证书的 24 个 raw-map 查询全部通过，home pad 的 N05 admission 也通过。

## 失败位置与几何原因

PX4 起飞到约 0.93 m 后，N08 发送前向 0.6 m 目标。目标开始时钟为 562.460 s；0.160 s 后 watchdog 以 `reference_control_hull_left_certified_trial_tube` 取消样条并进入 LANDING。实测第一条 position command 仅前移约 2.5 mm、向下约 3.4 mm；随后 action 被取消，未到达前向目标，没有终端制动保持、定点 yaw、返航或 N08 运动测量。

planner-observation 保存的 cubic B-spline 控制点中，最低点为 `(x=0.07462, y=0.00901, z=0.87856) m`。相对于起点 `(0.02621,0.00962,0.92928) m`，横向／垂向联合偏移为 0.05072 m，超过原 0.05000 m 管道约 0.00072 m。旧 watchdog 将控制点凸包直接当成实际轨迹来检查，因此在车辆尚未发生相应位移时拒绝了整条曲线。

对相同消息用现有 de Boor 评估器作 100001 点密采样，实际样条最大横向／垂向联合偏移约 0.04758 m；前向 x 偏移范围约 0.00148–0.60000 m。该密采样是诊断证据，不作为采样间连续安全证明。#266 将在原 5 cm 管道内检查实际曲线，并用样条速度上界和半采样间隔给采样间最大偏移留出保守余量；不会抬高 5 cm 限值。

## 安全末态与结论

`flight.json` 为 `FAIL`，`action_success=null`，failure=`reference_control_hull_left_certified_trial_tube`。桥经历 TAKEOFF→ACTIVE→LANDING→LANDED。任务结束后直接 ROS 读回 PX4 `arming_state=1`、land detector `landed=true`；bridge phase=`LANDED`、`control_enabled=false`、`armed=false`、`landed=true`。`bash tools/project.sh stop n08-20261025-265-yaw-first-return` 退出码0；当前无本项目运行容器。

扫描期间关闭额外 observer 与扫描完成在时序上相符，但 #264/#265 是不同冷启动，不能据此证明 observer 是 #264 telemetry_stale 的原因。N08 仍为 `in_progress`；此轮没有制动、转头或返航通过结果。

## 关键证据与哈希

- mission：`artifacts/runs/n08-20261025-265-yaw-first-return/flight.json`，SHA256 `b39985f13594bb448015697ddc3725413ade5aac9a988d31eef45f33647c925e`。
- B-spline：`artifacts/runs/n08-20261025-265-yaw-first-return/planner-observation.json`，SHA256 `3006f4b5dcc4d8cd9fe60d9653c9567dd8be81e47bcb13369d9bd03a362a65e9`。
- N05 mission current-area：`artifacts/runs/n08-20261025-265-yaw-first-return/n05-current-area/n05-live-entry-check.json`，SHA256 `256fa3ca19e2362337c0b1e653927e6faeb335dec0c539136b2a4a8f59a72478`。
- N05 run summary：`artifacts/runs/n08-20261025-265-yaw-first-return/n05-run-summary.json`，SHA256 `9af050f50d8b806ba98c2caefe0d2ba826fc207609a0de00bdfff51c21e47b0c`。
- N08 pre-enable raw-map/corridor record：`artifacts/runs/n08-20261025-265-yaw-first-return/n08-trial-pre-enable-admission.json`，SHA256 `938df029eb4987ba34b025f894cd044ad47b9ce4734c57d837b767c1aa895c62`。
- Independent braking evaluator：`artifacts/runs/n08-20261025-265-yaw-first-return/n08-braking-evaluation.json`，SHA256 `78016d31cadb4e7c9dde9bdac73a12ca44a8164a685a2c0ac2a4df7c64174dcd`；未找到 `post_goal_hold_end_sim_ns`，因此没有制动测量。
- 最终 launch manifest：`artifacts/runs/n08-20261025-265-yaw-first-return-stack/launch-manifest.json`，SHA256 `7679e9b0b3f498dbb90fdc2a8b34211853a26c6bd3f57bbfd7f433ffd2c7753c`。

后续 #266 仅更新 N08 的 spline 管道 watchdog 判定／相应定向测试，重建对应执行环境后使用全新 epoch、fresh N05 与相同速度配置重试。用户要求的返航顺序仍为原地 yaw 约 180° 后按 EGO 机头前向规则返航，严禁倒飞。
