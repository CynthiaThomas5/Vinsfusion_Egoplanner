# #361 N10 定位门限删除与校准协议

关联对话：[2026-10-27 #361](../../collaboration/dialogues/2026-10-27-361-n10-health-gates-removed.md)

## 改动

- 从目标配置删除 `acceptance_calibration_limits` 中没有实际执行、且没有 N10 证据支持的旧候选值。
- 从 `run_vio_ego_flight.py` 删除对该死字段的空类型检查。
- 为移除运行门限后的 #361 SITL 冷启动冻结独立 driver、离线 analyzer、goal/planner/spawn、full runtime contract 与前置判据。
- 离线 analyzer 不再从 health.json 读取活动 `max_normalized_cost`；历史 1.0 只标记为离线参考，不作门控或通过判定。

## 验证

- `bash tools/project.sh test`：413 项单测通过，navigation adapter 集成通过，official EGO policy 集成通过。
- 冻结 driver `bash -n` 通过；analyzer Python compile 通过。
- 门限删除后的 17 包 ROS 构建已在本轮稍早完成；本次额外修改仅涉及 runner/config/离线分析器，不改 ROS 编译源码。
- #361 runtime contract：`fdf104f5bd7b733128656fc4736af001f9ecdcbe1d93de123b41c7974a511a2f`（665 files）。协议和 prelaunch 指纹见 [#361 protocol](../evidence/n10-health-gates-removed-speed080-16m-protocol-20261027-361.md)。

## 运行状态

SITL 已完成；#361 全任务、观察器与独立 landed/disarmed/control-disabled/zero-control readback 通过后停止本项目容器，状态 exited。详细运行数据续记于下方 #361 SITL 结果。

## #361 SITL 结果

- 冻结 runtime SHA 与启动后 snapshot 相同：`fdf104f5bd7b733128656fc4736af001f9ecdcbe1d93de123b41c7974a511a2f`；有效参数 `max_vel=0.8 m/s/axis`、`max_acc=0.25 m/s²/axis`、horizon=5m、official_ego。
- action 成功；独立位置+yaw驻留 3.0187s，最小真值位置误差 0.0531m；600/600 仿真秒 ACTIVE hold 完成，RTF=0.761。
- normalized cost p95/max=1.2547/3.2712；首次高于历史 1.0 参考在 source 194.8s。没有质量门限锁存；状态有效，任务完成。1.0 只用于离线对照。
- raw VIO 位置 p95/max=0.3142/0.3234m，yaw p95/max=5.691/5.854°；EGO 跟踪误差 p95/max=0.5016/1.0311m；map source/occupancy age max=0.160/0.112s；EGO/PX4 向量速度峰值=0.691/0.626m/s。
- 禁止接触0；五个观察器均看到 flight terminal record；独立6秒 bridge readback 确认 LANDED/disarmed/control disabled/zero control，之后仅停止本轮容器且 exited。
- 未测障碍净空、replan 或故障响应。单次run不闭合重复性，N10.3 继续 active。机器报告：[evidence](../evidence/n10-health-gates-removed-speed080-16m-20261027-361.md)，原始数据 `artifacts/runs/n10-20261027-361-quality-gates-removed-speed080-16m/`。

首次 driver preflight 尝试因快照文件名错误提前退出，未发 goal/enable；修正记录和安全读回已归档，并在首个动作前更新协议哈希。
