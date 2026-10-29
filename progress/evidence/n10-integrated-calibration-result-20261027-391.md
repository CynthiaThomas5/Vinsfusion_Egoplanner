# N10.3/#391 综合校准结果

## 结论

本次运行取得了可用的单次到达、VIO/跟踪、接触、地图快照和离散物理步证据，但在目标完成后的保持段发生明显漂移、先触碰墙体，随后定位完整性锁存，任务未完成。PX4 状态历史先显示 `AUTO_LAND`（`nav_state=18`），随后转为带 failsafe 的 `DESCEND`（`nav_state=12`）；飞行记录结束时仍 armed，未达到 PX4 landed/disarmed。故障前后没有保存可将 NAV_LAND 命令与具体 ACK 关联的记录，因此只报告观察到的状态序列，不将它归因于命令已确认执行。运行整体失败，N10.3 不通过，N10 父目标继续 `in_progress`。

原报告记录运行当时容器仍在运行。PX4 历史于仿真源时间 273.916 s（飞行记录 wall elapsed 139.887 s）进入 `AUTO_LAND`；于 278.032 s（wall elapsed 144.261 s）转入 failsafe `DESCEND`，其后保持 armed。紧急命令前的独立读回仍为 bridge `LANDING`、armed=true、landed=false、control_enabled=true，PX4 nav_state=12、failsafe=true；Gazebo ground contact 没有对应 PX4 LandDetected。随后用户明确授权一次紧急 disarm 与受控停止，独立读回确认会话安全关闭。该后续收尾没有改写原始 `safe-to-stop.json`，也不把 #391 变为原生故障降落通过。

## 运行身份和证据

- Run：n10-20261027-391-integrated-calibration-retry。
- runtime contract SHA-256：86debc3c5817dc311b9d929ec6669812d4d69a9bef069a6fa65a58903aaeee01；启动后且目标提交前，源码、安装和实际运行身份核对通过。
- 工具冻结记录：artifacts/runs/n10-20261027-391-integrated-calibration-retry/n10-tool-freeze-used.json；协议 SHA-256 3788cdb3f65909f6e9d397bbac7e06fea45b0757fdd1901bcccd4f255b175072。
- 任务复用 #390 的 16 m 目标、4 s native dwell、动态箱体和 60 仿真秒诊断保持；控制和碰撞策略没有增加项目自定义健康门。轨迹控制唯一由 uav_px4_bridge 发布；真值与全部评估保持离线只读。
- 原始数据和运行日志：artifacts/runs/n10-20261027-391-integrated-calibration-retry/。

## 量测

- 目标段独立真值位置/yaw 同时满足既定 0.30 m、15°合同的最长连续窗为 3.980 仿真秒，996 个样本，最大位置误差 0.29961 m、最大 yaw 误差 8.90°。这一项单独支持到达驻留量测；总 mission 仍失败，不能据此记作 N10.3 通过。到达报告为 n10-arrival-evaluation-diagnostic.json。
- 目标动作段有 5,774 个命令/真值配对，最大真值 bracket gap 0.004 s。跟踪误差 P50/P95/P99/max 为 0.5355/0.6225/0.6412/0.6551 m。0.60 m 仍是待论证的离线候选，必须结合路线和机体净空解释，不能删除候选或把它变成运行时分支。见 n10-tracking-clearance-diagnostic.json。
- 目标动作期间每个配置的 4 ms Gazebo solver 状态均有记录：12,903 个样本，零 off-grid，最大步序差 1；收到状态的最小全机净空为 0.10604 m（unit_cylinder_4）。端点间每步观测到的包络运动最大 0.003524 m，仅为观测值，并非连续时间动力学上界。见 n10-action-physics-step-clearance-diagnostic.json。
- 之后的保持段只记录到定位 integrity lock 前 49.304 仿真秒，60 秒请求未完成。位置误差 P95/max 8.312/8.349 m；yaw 误差 P95/max 1.420/32.187°；目标后 7.468 秒首次离开 0.30 m 位置球。故障附近经单次固定 SE(3) 的 raw VINS 与真值差 5.046 m。见 n10-partial-hold-drift-before-localization-lock.json。
- 同一 4 ms 物理步重放覆盖从目标完成到首次违规接触的 12,273 个状态。Wall_1 的估算机体包络净空首次降至 0 的时间为 271.072 s；随后在 273.228 s 出现真实 rotor_0/Wall_1 接触。当时 bridge 仍为 ACTIVE。首次接触前后共有 86 个禁止的 rotor-to-wall 接触事件。该时间线纠正了“目标动作期间正净空”和“后续墙体碰撞”的表面矛盾：它们属于不同阶段。离散几何结果仍不构成连续时间认证。见 n10-partial-hold-physics-step-clearance-diagnostic.json 和 n10-contact-evaluation-partial.json。
- 273.444 s，定位适配器因 `propagated_invalid_quaternion` 进入 LOST。故障快照记录 stereo features=6、long tracks=0、继续跟踪=0；state finite/solver usable 仍为 true。normalized cost=5.023 仅作观察，不作为本次触发门。此后 EGO map/odom 停止，上游 watchdog 触发 `full_curve_depth_odom_timeout`；bridge 请求 PX4 `NAV_LAND`。本地位置无效、EV 融合标志关闭。PX4 状态历史显示先为 `AUTO_LAND`（18），随后在 pre-flight 检查失败时转为 failsafe `DESCEND`（12）；未检测到原生 landed/disarmed。故障顺序支持“先漂移/接触，再定位完整性锁存，再 planner timeout 和 land request”，不证明 NAV_LAND ACK，也不支持将观察器归因于失败。
- 同一地图快照 identity 稳定；raw/inflated 数组与方箱表面统计保存在 n10-box-map-snapshot-analysis.json。26 条 raw sphere/planning point 查询的响应身份及中心匹配，但离线 capture 因未序列化响应 radius 而标记 incomplete；不得把服务捕获记为通过，也不得覆盖原始捕获。见 n10-map-point-queries.json。
- 资源观察只覆盖 193.6 wall 秒，报告在终态飞行记录后中断。RTF P50/P95/max 约 0.898/0.917/0.944；cgroup memory P95/peak 约 2.524/2.673 GB；CPU usage P95/max 约 7.23/10.62 核；queue depth high-water 8。队列 drop 在定位锁存之后继续增长到 1,344，因此不能倒推为最初故障原因。主机暴露 64 CPU，cgroup CPU/内存无有限上限；这些值只描述本平台，不足以建立 N16 平台容量合同。

## 结论边界与后续

- 到达驻留、跟踪、目标段净空和 4 ms 离散真值覆盖取得有效诊断样本；保持漂移、真实碰撞和 PX4 terminal failure 是反证，不能把这些指标记成通过。
- 查询 observer 的响应几何回显仍不完整；资源 observer 仍是部分记录。对应指标保持 INSUFFICIENT。
- #391 已完成授权后的安全关闭，但仍是失败运行，不计 N15 正式故障次数，也不计 N16 十分钟验收。后续先审计并验证故障结束路径、采样间净空方法、误差相对通道预算及观测器关闭条件，再决定需补采的校准证据。
- 完成证据整理和状态更新后，N10 仍 in_progress。最终冻结必须有可靠故障退出、场景支持误差预算、有效查询/资源采集、干净 ROS/PX4 重建以及重建后完整任务证据。
