# N10.3 #361：移除项目定位门限后的 16 m 校准结果

状态：**诊断运行完成，N10.3 仍未通过。** 当前 runtime 的定位质量和定位/优化里程计回执龄门限已删除；本结果只报告测量，不冻结正式预算，也不计入 N11–N16。

## 任务与安全终态

- 冷启动 ID：`n10-20261027-361-quality-gates-removed-speed080-16m`；goal action 成功，单目标真值评估的位置与 yaw 同时达标驻留 `3.019s`，要求 `3.0s`；最小三维位置误差 `0.053m`。
- 目标后 ACTIVE 保持 `600.0/600` 仿真秒，RTF `0.761`；保持起止定位差 `0.019m`。随后 PX4 桥降落。
- 独立真值评估：禁止接触 `0`；地面接触 `14725`。PX4/bridge 读回 `LANDED`、landed=true、armed=false、control_enabled=false、车辆全程保持 disarmed、控制样本为 0。driver 生成 `safe-to-stop=true` 后，仅停止本项目容器；现容器状态 `exited`。
- 五类终态观察器（truth、alignment、planner、bridge、contact）均有 `terminal_flight_record_observed=true`。

## 门限移除后的运行表现

raw normalized cost 共 `10152` 个样本，p95 `1.255`、峰值 `3.271`；首次越过历史 1.0 对照值在 wall `84.04s`、source `194.800s`，随后最高达到 3.271，定位状态仍有效并完成任务。**历史 1.0 只作离线对照，不是门限、故障判据或本报告 PASS 条件。** 无效定位状态样本 0。

## 量测摘要

| 指标 | #361 观测 | 解释边界 |
| --- | ---: | --- |
| Raw VIO 位置误差，PRESTREAM–LANDED 单次固定对齐 | RMSE 0.182m；p95 0.314m；max 0.323m | 含起飞/降落，覆盖 666.0s、真值配对路径 22.970m |
| Raw VIO 绝对 yaw 误差 | RMSE 3.052°；p95 5.691°；max 5.854° | 单次固定对齐，不能代表所有姿态/运动 |
| Raw/真值时间覆盖 | support 0.999898；source max gap 0.068s；truth max gap 0.020s | 本次记录范围内的采样统计 |
| EGO READY 命令对真值跟踪误差 | median 0.169m；p95 0.502m；max 1.031m | 固定 preflight SE(3)，无分段重拟合；不是制动误差 |
| 地图 source / occupancy age | max 0.160s / 0.112s | 从目标发送至落地的 map 状态采样；旧 0.4s 不是冻结标准 |
| EGO / PX4 实际向量速度 | max 0.691 / 0.626m/s | EGO 参数是逐轴 0.8m/s；速度仅观察，无外加运行速度 guard |
| 地图/定位/clock receipt gap | localization 0.161s；odom 0.224s；map 0.253s；clock 0.131s | 来自 0.1 wall-second 降采样时间线，不是精确 callback gap 证明 |

## #361 未闭合的 N10.3 指标

本次世界实际包含 `ego.sdf` 中的 23 个非地面静态碰撞形状。最初运行报告未运行独立净空 evaluator；后续 #363 已用同一运行的真值、加载 SDF 与当前 runtime 包络离线复算，采样最小净空0.35284m，扣除相邻样本最大包络运动后为0.33791m。该扣减不是连续动力学上界，不能作正式净空资格。该任务没有动态障碍注入／重规划或故障注入；也没有重复冷启动来确认误差/漂移/时效重复性。到达评估虽通过位置+yaw联合驻留，但原输出未保存该窗口 yaw 误差分布。详见[#363 静态净空复算](n10-clearance-static-world-replay-20261027-363.md)。

另外，首次 driver 启动因当前 runtime 快照文件名拼写不一致而在 preflight 前退出；无导航目标或 enable 请求。修正前独立 3 秒读回确认仍为 DISABLED/landed/disarmed/control0。过程保留于 `driver-preflight-attempt-01.log` 和 `setup-preflight-readback.json`；修正 driver 后才执行任务。

完整原始包：`artifacts/runs/n10-20261027-361-quality-gates-removed-speed080-16m/`。核心机器评估器：[n10-calibration-evaluation.json](../../artifacts/runs/n10-20261027-361-quality-gates-removed-speed080-16m/n10-calibration-evaluation.json)；独立到达报告：[arrival-evaluation.json](../../artifacts/runs/n10-20261027-361-quality-gates-removed-speed080-16m/arrival-evaluation.json)；独立 contact 报告：[vehicle-contact-evaluation.json](../../artifacts/runs/n10-20261027-361-quality-gates-removed-speed080-16m/vehicle-contact-evaluation.json)。输入哈希及协议修订见本报告的 [JSON](n10-health-gates-removed-speed080-16m-20261027-361.json) 与 [冻结协议](n10-health-gates-removed-speed080-16m-protocol-20261027-361.md)。

下一子项：冻结 PX4 动态障碍／实际 EGO 重规划的有界诊断协议，并补当前 gate-free runtime 下长程 VIO 误差／时效重复样本。N10.4 的唯一正式验收配置尚不能冻结。
