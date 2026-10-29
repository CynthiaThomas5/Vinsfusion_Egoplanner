# N09 三维航点与任务反馈验收

## 控制链与接口

简单航点使用现有 `/navigation/navigate_to_pose` (`uav_interfaces/action/NavigateToPose`) 提交完整三维目标、四元数航向、位置/yaw 容差、驻留时间和超时。导航节点检查当前 `odom_<epoch>`、定位/里程计新鲜度、地图身份和飞机 ACTIVE 状态；以官方 inflated-occupied point predicate 查询目标（radius=0），unknown 不单独拒绝；通过后发布带 `goal_id + epoch + map_id` 的 `NavigationCommand`。EGO 负责原生膨胀障碍轨迹规划和在线碰撞检查；#331 官方模式停用额外 raw-known-free 整曲线／终点保持球门禁，`traj_server` 发布 `PositionCommand`，唯一 `uav_px4_bridge` 将它变成 PX4 Offboard 设定点。

因此“简单航点”是目标输入形式，EGO 是规划器；它们共用同一 action、地图准入和 PX4 控制出口。没有第二个直线插值控制器。旧 `/move_base_simple/goal` 直通已关闭，因为它固定高度为 1 m 且绕过 goal/epoch/map 准入。

CLI 请求示例（坐标是 `odom_<epoch>` 中的绝对位置，不是相对位移；实际使用时先通过实时地图准入选点。runner 会从起飞后当前位姿加上候选偏移；yaw 使用弧度）：

```bash
ros2 action send_goal --feedback /navigation/navigate_to_pose \
  uav_interfaces/action/NavigateToPose \
  "{target: {header: {frame_id: 'odom_<current-epoch>'}, pose: {position: {x: 0.4, y: 0.0, z: 0.1}, orientation: {z: 0.0998334, w: 0.9950042}}}, position_tolerance_m: 0.05, yaw_tolerance_rad: 0.1, dwell_s: 1.0, timeout_s: 60.0}"
```

## 动作矩阵

| 场景 | 主要判据 | 证据来源 |
|---|---|---|
| 有效三维目标 | 目标包含非零水平与高度差、不同 yaw；action 到达与独立 Gazebo 真值一致；位移大于容差 | PX4 SITL、`NavigateToPose` 结果、只读真值与 `arrival-evaluation.json` |
| 显式 caller cancel | action 终态为 CANCELED；按 goal/epoch 发 STOP_HOLD | ROS action 集成回归；N08 的实测 STOP_HOLD 资格仍沿用原范围 |
| 活动任务替换 | 旧 action 以 `ABORTED / goal_replaced` 结束；新 goal id 继续；不为正常替换发送轨迹 ABORT；旧 goal fault 不得影响新任务 | ROS action/EGO 接口集成回归；需要时再加 SITL 手动替换跑次 |
| 目标超时 | action 在 wall deadline 内以 `ABORTED / goal_timeout` 结束，并按当前故障路径清理轨迹 | 合成 ROS action 集成回归 |
| unknown/occupied/越界/过期或不可达 | unknown 保留原始分类，官方 point query 未命中膨胀障碍时可转发；occupied/越界/过期/不可达给出明确拒绝、planner fault 或超时终态 | 新官方模式 ROS 集成与 SITL live planning/raw 对照；旧 known-free 回归单独保留 |
| stale goal/epoch/map | 旧 goal id 不影响当前任务；旧 epoch 拒绝；map identity 改变中止活动任务；EGO query 绑定旧 map 时拒绝 | ROS action/EGO 接口回归与逐 run map identity 时间线 |

## SITL 候选与执行顺序

候选配置为 `config/components/navigation/n09_3d_waypoint_goal.json`：从初始悬停位姿前进 0.4 m、升高 0.1 m、终端航向增加 0.2 rad；native 容差分别为 0.05 m 与 0.1 rad，驻留 1 s。该 3D 位移目标约 0.412 m，是位置容差的 8 倍以上；航向变化是 yaw 容差的 2 倍。先单次 pilot 检查视场、EGO 曲线证书、真值到达、落地与源龄，再锁定配置/构建身份并做 3 次独立冷启动。pilot 不计入 3 次。

每次冷启动都要求：

1. 任务前桥 DISABLED、PX4 landed/disarmed；读只 preflight 通过。
2. 按官方独立起飞状态门检查已着地、未武装、无控制、VINS/PX4 状态有效和速度≤0.1m/s；N05 raw 包络与支架扫描不作起飞前置。
3. 飞机进入 ACTIVE 悬停后才转发导航目标；采用原生 inflated occupied 判据，不追加 raw-free 全曲线/hold 球认证；raw unknown 保持为 unknown。
4. 任务落地后用当前新鲜 epoch/map 做一次实时地图外目标拒绝探针：action 返回 `map_query_outside_map`，无 EGO 转发，桥保持 LANDED／未解锁／控制关闭。
5. 从 goal 发送前到任务结束，定位/里程计和 MapStatus 的 epoch、map_id、source/fusion 时间连续且新鲜。
6. action 成功、匹配该 goal/epoch 的 EGO `PositionCommand` 到达 bridge、实际真值位移明显大于容差；独立真值在规定容差内持续满足位置和 yaw。
7. PX4 模型运行时覆盖为观测用 contact sensor，覆盖机身、四个旋翼和相机外壳；六个话题须在起飞前全部存在。任务活动期间任何地面接触或与障碍物接触均失败；起飞前地面接触和 LANDING/LANDED 阶段的正常地面接触允许。必须实际观察到着陆地面接触，以证明观测流工作。
8. 最后 PX4 landed/disarmed、bridge LANDED/控制关闭。N09 跑次只做单程目标；PX4 自动正常着陆不表示任务返航，也不执行隐式返航。

三次必须用全新 simulation run id、epoch、map_id 和 PX4 SITL build copy；profile、runtime-contract、EGO patch chain、安装二进制与 evaluator 身份相同。三次诊断结果不计入 N11–N14 正式场景次数。

启动方式示例（host；每次使用新 RUN_ID）：

```bash
D435I_N08_MODE=execute \
D435I_N09_CONTACTS=1 \
D435I_PLANNER_CONFIG=config/components/mapping/n08_low_speed_trial.json \
bash tools/project.sh sim "$RUN_ID"
bash tools/project.sh n09 "$RUN_ID" config/components/navigation/n09_3d_waypoint_goal.json
```
