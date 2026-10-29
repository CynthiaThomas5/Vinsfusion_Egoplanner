# N10.3 综合采集校准结果：#396

日期：2026-10-27
运行：`n10-20261027-396-integrated-capture-calibration`
分类：一次成功完成任务的校准运行；验收总状态 `INSUFFICIENT`，不计冻结后正式次数。

## 任务和安全末态

16 m EGO 目标成功，控制器报告 `position_yaw_tolerance_held`；独立真值同时位置/yaw 窗口为 3.436 仿真秒，随后 ACTIVE 诊断保持 15 仿真秒。飞行记录为 `PASS`、`action_success=true`、`landed_and_disarmed=true`。独立 PX4/bridge 读回保持 landed、disarmed、failsafe=false、控制关闭且终态控制样本为零；容器正常退出。此次没有触发故障，也未使用紧急 disarm，因此不能用于证明故障降落路径。

## 可复用的校准观察

- 真值评估覆盖目标至落地共 19,067 个 4 ms Gazebo 状态。静态场景采样机体包络最小净空为 0.228263 m；观测到的相邻求解状态包络移动最大值为 0.005077 m。该差值只描述已记录的离散状态，不构成连续时间运动界或正式净空证明。方箱本身采样最小净空为 1.213409 m。
- 任务段 7,999 个跟踪/几何配对中，EGO 位置跟踪误差 P50/P95/P99/max 为 0.559/0.707/1.379/1.502 m；同一 PX4 本地坐标域的设定点到位置误差 P50/P95/max 为 0.538/0.665/1.521 m。仅用于诊断的 1.08 s 设定点回看对应 P95 0.256 m；这是相关性结果，不能解释为已测得的物理或软件延迟。点对点平移净空下界在 25.28% 的样本为负，不能保证全路线正余量。
- 方箱创建收到 Gazebo ACK。原始障碍点云在插入后 3.588 仿真秒首次出现；密采样中心线分析在 +3.944 s 首次看到轨迹对箱体有正距离，在 +4.348 s 首次超过 0.482 m 的机体水平扫掠半径。该分析不是全机连续净空证明。4 ms 真值轨迹计算的箱体净空与上述规划中心线分析分别报告，不混成同一指标。
- 唯一 raw/inflated 数组快照 identity 匹配，但在插箱后 +1.016 s 采集，箱体内部为 1,792 unknown、0 known-free、0 raw-occupied，表面附近 raw/inflated occupied 也均为 0。点查询 `/mapping/get_map_status` 不可用，查询数为 0。此快照不能证明箱体表面已进入规划地图；下一运行只需把快照观察时刻延后到点云出现之后，并保留同一快照的 raw/inflated 数组及 identity。
- 左/右目和 IMU 的记录完整性离线评估 `PASS`：83,012 条 bag 消息、83,065 条收据，active identity tuple 数为 1；无 payload 内部缺收据或时间戳倒退。队列容量记录仍无法解析 VINS 内部队列容量。资源观察持续 378.17 wall s 并观察到安全终态；它覆盖本次短诊断负载，不替代 N16 十分钟负载标准。
- raw VIO 的绝对位置/yaw 候选比较通过；10 s RPE 平移 P95 为 0.1057 m，高于 0.05 m 临时候选；goal-motion 速度误差 P95/max 为 0.05168/0.10220 m/s，高于 0.05/0.10 m/s 临时候选；地图 source/occupancy update age 最大为 0.392/0.284 仿真秒，高于 0.20 s 临时候选。以上是草案支持性结果，不调整或删除候选门限。

## 评估状态与工具缺口

离线判断器总体为 `INSUFFICIENT`（14 项：到达 PASS、raw VIO 绝对误差 PASS；RPE、速度误差、地图时龄按临时候选 FAIL；跟踪/净空、全机净空资格、地图表面/分类、动态重规划、故障终态、资源/队列、observer 身份完整性仍不足）。SITL 任务本身成功，但 run driver 最终退出码为 1：归档分析脚本期待旧到达字段并抛出 `KeyError`；地图快照分析被调度在 sim-time 到达别名生成前；tracking/clearance 分析在动态世界 SDF 生成前运行。各原始结果保留，离线复算已补出本报告中的几何与跟踪值；后续 driver 应按输入依赖排序并将“任务成功”与“离线证据状态”分别汇报。

## 身份和复算输入

runtime contract SHA256：`658080ae4ed11f6d58540166573cdd3142818e69c9991ce279e71e6972364ebd`。关键原始文件 SHA256 见 [配套 JSON](n10-integrated-capture-result-20261027-396.json)；全部原始日志、录包、数组快照与真值数据保留在 `artifacts/runs/n10-20261027-396-integrated-capture-calibration/`。跨 epoch 的 #381/#385 数据不与本次样本拼接。

## 后续

N10 继续 `in_progress`。下一项 #397 仅将 EGO planner `max_velocity` 从 0.8 降至 0.4 m/s，其他控制参数、场景、spawn、目标和故障路径保持不变；observer-only 地图快照改在方箱首次进入点云后的窗口采集，净空评估用已记录的 4 ms physics states。目标是判别降速是否改善真实跟踪误差与场景净空预算，并补齐地图表面 raw/inflated 快照，不把任何离线越线结果接入飞行拒绝、取消或降落分支。故障到 PX4 landed/disarmed 的端到端当前版本 SITL 证据仍须单独补齐。
