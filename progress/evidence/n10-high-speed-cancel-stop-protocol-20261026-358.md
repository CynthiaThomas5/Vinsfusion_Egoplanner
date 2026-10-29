# #358 N10.3 高速取消制动测量协议

## 目标与唯一主要变量

测量同一 N10 16 m EGO 诊断路线在 PX4 本地位置速度首次进入水平速度 0.50–0.56 m/s 时收到调用方取消后的响应和实际停止距离。唯一主要变量是取消触发速度窗口；不改变路线、EGO 参数、膨胀、健康阈值或控制桥。

该窗口覆盖 #357 已测峰值 0.636 m/s 的高速段，明显高于 N08 已有约 0.081 m/s 的制动样本。本次只取得一个代表性诊断样本，不把它解释成速度范围保证。

## 固定运行条件

- 单 D435i Gazebo/PX4 SITL，spawn 和 +16 m/+0.10 m/+0.20 rad 目标与 #357 相同。
- EGO 参数固定为 max velocity 0.8 m/s/轴、max acceleration 0.25 m/s²/轴、planning horizon 5 m；采用运行时加载值核对。
- `D435I_DIAGNOSTIC_BYPASS_HEALTH_GATES=1`；运行中确认旁路状态，同时保留原 normalized-cost 1.0 阈值和原始代价值记录。
- 起飞后由唯一 navigation action 发一个前向 EGO 目标；达到 PX4 水平速度窗口后只取消一次。等待 EGO 生成不同 trajectory id 的替代停止轨迹，并继续观察到 PX4 水平速度 ≤0.03 m/s、垂向速度绝对值 ≤0.05 m/s 连续 1 个仿真秒，然后由 `uav_px4_bridge` 正常落地。
- 碰撞策略维持 `official_ego`，EGO 使用上游 inflated occupied layer。取消试验不运行项目额外的 raw-free 全曲线／capsule 拒绝检查；定位 epoch、时间完整性、地图身份/时效、EGO 自身规划碰撞处理、PX4 freshness 与桥控制状态仍保持。

## 记录和判据

独立记录 `/clock`、PX4 local position、EGO PositionCommand/trajectory id、planner、bridge、Gazebo 真值、contact 和定位状态。保存目标请求、取消请求、取消确认、替代轨迹首次发布、首次进入停止带和停止带完成时刻。

报告以下实测量：取消时 PX4 水平速度和 EGO 参考速度、取消确认延迟、替代轨迹延迟、从取消请求到停止带首次进入的 Gazebo 真值水平路径长度与仿真时间、停止后 1 秒位置变化、实际减速曲线、碰撞接触、定位/地图状态及终态 PX4/bridge 读回。真值只读，不进入控制。

一次运行的有效测量需要：触发速度实际落在窗口内；调用方取消被确认；观察到新 EGO trajectory id；PX4 停止带持续 1 秒且 PX4 sample 时间单调、间隙不大于 0.20 秒；真值覆盖完整制动区间且最大间隙不大于 0.04 秒；contact observer 完整且无禁止接触；独立末态读回为 LANDED/disarmed/control disabled/zero control samples。任何缺失均判为不可量测或失败样本，不通过提高阈值补救。若 EGO 未生成替代轨迹、健康旁路外的硬完整性条件失败或桥离开 ACTIVE，立即由原桥停止/降落流程收尾。

## 解释边界

停止速度带和 1 秒驻留复用 N08 当前仿真测量定义；0.20 秒 PX4 sample gap 与 0.04 秒真值 gap 是本次离线测量支持条件，不是飞行安全阈值。该运行不能关闭 N08 出口、正式健康资格、净空预算或速度上界；只有在重复和独立净空证据齐备后才可评估最终可支持范围。

结果目录预留为 `artifacts/runs/n10-20261026-358-high-speed-cancel-stop/`。
