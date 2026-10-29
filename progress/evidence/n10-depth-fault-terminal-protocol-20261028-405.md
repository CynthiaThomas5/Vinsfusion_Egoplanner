# N10.3/#405 深度断流自然终态校准协议

## 目的与范围

对当前冻结运行组合做一次诊断校准：在活动 EGO goal 的 source stamp 后 2.0 仿真秒开始，仅丢弃 D435i depth 输入 3.0 source 秒，再恢复转发；观察 EGO 原生 `depth_odom_timeout`、导航 action、bridge/PX4 自然落地上锁和独立末态读回。该次运行不属于 N15 正式重复次数，也不建立额外健康门或运行阈值。

运行身份：`n10-20261028-405-depth-timeout-terminal`。

## 固定输入

- Goal：`config/components/navigation/n10_long_range_vio_dwell4_capture_calibration_goal.json`（16 m 诊断路线、4.0 仿真秒原生驻留；任何后续保持都不作本项要求）。
- EGO：`config/components/mapping/n10_horizon5_speed040_calibration.json`（速度参数 0.4 m/s、加速度 0.25 m/s²、horizon 5 m、深度/里程计超时 0.4 仿真秒）。
- Spawn：`config/components/simulation/n10_long_range_spawn_minus8.json`。
- Sensor bridge：`config/components/simulation/n03_depth_fault_bridge.yaml`。Gazebo depth 单独进入 `/fault/input/depth`，fault relay 再转发到 `/sensors/d435i/depth`；左右双目和 camera IMU 仍由桥直接发布。
- Fault relay：`tools/fault_relay.py --kind depth --after-goal-s 2.0 --drop-for-source-s 3.0`，按活动 goal source stamp 调度，半开区间；relay 不发布控制或真值。

## 运行前核对

1. 无其他项目仿真容器；新 run 目录不存在。
2. 固定镜像、实际 launch manifest、runtime contract、goal/planner/spawn/bridge 文件及哈希一致。
3. bridge 原生 preflight、当前控制图和起飞准入可用。控制图必须仍由 `uav_navigation` 唯一发布 `/navigation/ego_goal`，由 EGO、PX4 bridge、只读 sensor capture 和 fault relay 订阅。
4. `/fault/input/depth` 有一个 Gazebo bridge publisher 和一个 relay subscriber；`/sensors/d435i/depth` 由 relay 发布；左右图像与 IMU 仍各有直接 sensor publisher。
5. 无 goal/arming 后才继续；任何路由身份不符都只在起飞前停止本次注入准备，不改在线控制策略。

## 观察与判定

只读观察包含物理真值/接触、planner、bridge、资源和 MCAP/源戳收据。observer 或 evaluator 状态不改变起飞、取消、降落决策。

校准 `PASS` 需同时具备：depth 在窗口前转发、窗口内实际丢弃、窗口后恢复；fault trigger 的 goal/epoch 与飞行记录一致；窗口内左右图像和 IMU 收据持续存在；EGO 记录 `Depth Lost!` 与 `depth_odom_timeout`；action 以同一故障原因 abort；bridge 因该原生故障进入 LANDING 并达到 LANDED/disarmed；独立 PX4/bridge 末态读回完整且终态后无控制；没有 emergency disarm。

触发到 LANDING 的时间只报告观测值，不设通过阈值。缺失或身份不匹配均输出 `INSUFFICIENT`。action abort 后专用运行模式等待 bridge 自己完成落地，不调用 operator-disable；若没有观察到自然安全末态，则保持容器和只读观察器运行，不强停、不 emergency-disarm。

## 安全与解释边界

继续使用 PX4 原生 preflight、EV 融合、EGO 碰撞检查和输入超时。本次不恢复项目自加残差、经验速度、连续健康等待、raw-known-free 全包络等条件，不因 CPU 峰值、记录器或离线指标新增拒飞/暂停/降落分支。故障校准不能替代 N15 每类至少两次正式测试；N15/N16 仍在 N10 冻结后执行。
