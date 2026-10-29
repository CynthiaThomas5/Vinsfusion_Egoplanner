# #342 N10.3：0.31 m/s/axis 单变量候选结果

结论：**不通过，未测到长程飞行速度或 16 m 定位/地图支持。** planner 确实加载 `max_vel=0.31 m/s/axis`，但首次局部规划以 `terminal point ... in obstacle` 失败，EGO 在发布任何 READY 轨迹前中止。速度监视没有越限事件；它没有机会观察到 EGO 飞行轨迹。

## 任务与实际加载值

- 协议：[#342 执行前固定协议](n10-speed031-calibration-protocol-20261026-342.md)。单变量是 #341 的 0.10→0.31 m/s/axis；其他规划、相机、官方 `inflated occupied` 策略、+16.0 m / +0.10 m / +0.20 rad goal、PX4 参数及 0.12 m/s 三维向量门固定。
- Runtime contract 与 launch manifest SHA 证明实际加载候选文件；参数读回 `max_vel=0.31`、`max_acc=0.25`、`planning_horizon=2.0`、inflation=0.7306179 m、official policy=true。Goal由当前 odom frame接受，fresh preflight 和官方起飞准入均通过。
- 实际起飞后 mission goal 发出；EGO 日志在约 0.02 sim-s 内出现多次 `traj 1 failed`、`terminal point of the current trajectory is in obstacle, skip this planning` 与 `Full-curve safety rejected: planning_failed`。最终 `planner_full_curve_planning_failed`；0 READY trajectory，位置命令标志为空，没有水平目标位移、3s dwell 或600s hold。

## 拒绝原因诊断

这是几何/局部目标入口拒绝，不是速度门拒绝。当前 launch 从世界 x≈−6.5 m 起飞，局部 planning horizon=2 m。source world `simulation/worlds/ego.sdf` 在世界坐标约 (−4,0) 放置一根半径0.30m、高10m、中心z=−2.5m的圆柱；它延伸至z=+2.5m，覆盖当前约1m飞行高度。沿 +X 的预期首个2m local target约在x=−4.5m，距圆柱中心约0.5m，小于圆柱半径与 planner inflation 合计 `0.30+0.7306=1.0306m`。这与 planner 的 terminal-point-in-obstacle 拒绝相符。planner 没有输出被拒控制点坐标，因此此因果定位是由算法局部目标规则和世界几何支持的推断，而非精确运行点读回。

下一子项固定目标相对位移、planner=0.31、全部阈值和保护，只将 N10 专用冷启动 spawn 移到对称走廊内的x=−8.0m，使首个2m local target落到该圆柱后方；随后保留障碍前向重规划与速度监视，不绕过碰撞检查。该变量单独由 #343 协议锁定。

## 速度、定位和末态

- 运行保护沿用 goal 中原 `max_actual_vector_speed_m_s=0.12`。记录到一条 PX4 `VehicleLocalPosition` 三维速度样本，0.058756m/s；没有 READY EGO reference样本、没有超限和 cancellation event。这个单样本不代表飞行速度统计。
- 固定单次SE(3)、scale=1 的事后 raw VIO评估：PRESTREAM→LANDED共28.328 sim-s、paired path 1.8703m（起飞/降落），429样本；位置误差RMSE/p95/max=0.00335/0.00882/0.01169m，yaw误差RMSE/p95/max=0.00877/0.01938/0.03890°。这些只支持短程起降片段，不是16m或长时指标。
- 目标独立评估未通过：真实目标最小距离16.0012m、连续目标驻留0秒；这是因为没有执行路线，不是到达精度测量。
- Live refusal通过；contact评估通过，违规接触0，落地接触观测到。Runner与 independent postflight refusal均确认bridge LANDED、PX4 disarmed/control disabled。只停止本次 `d435i-n10-20261026-342-speed031-guarded`，容器exit0；`volant-height-route-probe` 与 `natfrp-service` 保持运行、未触碰。
- 以任务结束为界提前停止了1500秒 source-timeline observer；它不是本报告的长时效证据。任何未完成观测都不作通过。

## 产物与哈希

原始数据：`artifacts/runs/n10-20261026-342-speed031-guarded/`。关键文件哈希见结构化报告 [JSON](n10-speed031-calibration-20261026-342.json)。包含flight、VIO、goal/trajectory observation、contact、live refusal、arrival、odometry评估、PX4和launch manifest。

N10.3仍未通过：长程VIO/地图支持、障碍净空、重规划时延和源时效的量化依据缺失；#342没有产生路线速度/制动数据。
