# N10.3/#391 安全收尾与保持漂移复核

## 结论

#391 经用户一次性授权执行紧急 PX4 disarm，并受控停止项目会话。独立 3 秒读回确认 bridge `LANDED`、`landed=true`、`armed=false`、`control_enabled=false`，PX4 `arming_state=DISARMED`、`LandDetected.landed=true`，读回期间控制输出为零；项目 stop 正常退出且已无对应活动容器。这是本次会话的安全收尾，不构成 EGO/桥接的原生故障降落通过证据。原运行仍为失败，原 `safe-to-stop.json` 保持不变。

离线复核支持保持期间发生定位/测量与机体真值分离：在首次真实接触前，PX4 local position 相对固定 trajectory setpoint 的 P95/max 误差为 0.0456/0.0644 m、速度最大值 0.1084 m/s；同一保持段 fixed-prestream-aligned raw VINS 对真值位置误差 P95/max 达 8.298/8.334 m，真值相对目标 P95/max 为 8.313/8.349 m。VINS stereo feature 数从保持开始的 69 降至完整性锁存前的 6，long tracks 从 56 降至 0。证据表明独立真值在移动，而 PX4 local estimate 仍贴近其固定设定点；它不能唯一确定漂移起因。

故障顺序为：保持期间漂移；Wall_1 机体包络离散余量在 271.072 s 到 0；273.228 s 真实 rotor-to-wall 接触；273.444 s localization adapter 锁存 `propagated_invalid_quaternion`；随后 EGO 输入超时，桥请求 PX4 `NAV_LAND`。PX4 状态历史在 273.916 s 观测到 `AUTO_LAND`（`nav_state=18`），并于 278.032 s 转为 failsafe `DESCEND`（`nav_state=12`）；紧急命令前的独立读回仍 armed/failsafe/DESCEND、未 landed。归档没有命令 ACK 与 NAV_LAND 请求的可关联记录，因此不声称该请求已确认接受。PX4 `VehicleStatus.msg` 将 12 定义为 DESCEND（无位置控制）、18 定义为 AUTO_LAND。紧急 disarm 后状态为 nav_state=14（OFFBOARD），但当时已 disarmed、LandDetected=true、控制关闭且输出为零；这是会话关闭读回，不是原生故障着陆。

## 输入与可复算记录

- 运行目录：`artifacts/runs/n10-20261027-391-integrated-calibration-retry/`
- 运行身份：runtime contract SHA-256 `86debc3c5817dc311b9d929ec6669812d4d69a9bef069a6fa65a58903aaeee01`。
- 分析器：`tools/debug_truth/evaluate_n10_hold_divergence.py`；报告：`n10-hold-state-divergence.json`。使用单次 prestream scale-one SE(3)，不分段拟合，不向在线链路反馈真值或控制。
- 收尾命令、紧急后读回和终态摘要分别为 `emergency-disarm-command.json`、`emergency-disarm-postcheck.json`、`emergency-disarm-safe-terminal.json`。记录一条授权 force-disarm 命令及 3 秒独立读回。
- PX4 状态变化从原始 `flight.json.vehicle_status_history` 复算；枚举来自冻结依赖 `src/vendor/px4_msgs/msg/VehicleStatus.msg`。补正后的状态转移字段写入 `n10-hold-state-divergence.json`，原始读回及原始运行文件不修改。
- 部分总评：`n10-partial-acceptance-classification.json`。到达单项可判定，但完整任务、接触和原生故障终态失败；地图 query 与资源观察仍不足。
- 项目会话容器 `9eb759258919ef817f7266aa93cd09fd53e1125671717f17ebf00c414ebff40a` 已由项目 stop 关闭；本报告没有改写运行原始输入。

## 限制

- 缺少贯穿失败保持段的相机图像和左右目接收时间序列，不能区分视野/纹理变化、图像或 IMU 投递、估计器退化及其他起因。feature count 与 normalized cost 仅作离线观察，不能据此新增运行时门。
- raw VINS 定位时间线按 wall 时间抽样；稀疏定位输出不代表连续估计轨迹。真值物理步记录覆盖离散求解步，离散净空不等于连续时间碰撞证明。
- 首次接触后的 PX4 local velocity 峰值受碰撞影响，不能用于解释首次接触前的运动。
- 查询响应未保存 radius 回显，资源记录只覆盖 193.6 wall 秒；这两项仍为 `INSUFFICIENT`，不得以本次收尾补足。
- 紧急 disarm 由一次性授权的独立命令发布，不属于桥自身原生终态闭环；不计 N15 正式故障次数，也不满足 N10.3 的原生故障终态要求。

## 后续

N10.3 与 N10 继续 `in_progress`。下一步只读审计真实 EGO 输入超时和 planner 进程退出后从 abort 到 PX4 landed/disarmed/control-disabled/zero-control 的完整代码与观测路径；对 drift 原因保持未唯一识别。若确认实现缺口，先提交最小代码修复与定向验证，再准备受影响校准；N15 每类至少两次与 N16 连续十分钟留在 N10 冻结之后。
