# #347 N10.3：planner 0.25 m/s 候选校准协议

状态：**运行前冻结**。这是 #346 接口/校准复核后的单变量候选；EGO reference 与 PX4 实测都继续受 0.12 m/s guard 监控。这个 guard 是保守命令参考上限与实际速度上限的并集，reference 越线会取消；它不表示 PX4 已达到该速度。

## 假设与判据

#346 的首条非静止 B 样条 x 导数控制点为 0.314555 m/s，几乎达到 `.30 × 1.05 = 0.315 m/s` 的逐轴可行门；EGO reference 峰值为 0.124502 m/s，PX4 实测峰值为 0.062623 m/s。只有 planner 参数变化无法保证 reference 按比例降低。#347 唯一变量是 `max_velocity_m_s: 0.30 → 0.25 m/s/axis`，其逐轴门变为 0.2625 m/s，低于 #346 实测 x 导数约 16.5%。按理想时间缩放估算 reference 约 0.104 m/s，但先前 #345→#346 的比例估算未被实测支持；这个数仅作弱估算，不是验收指标。

成功的必要条件仍是完整单程 16 m EGO 任务原生成功、独立真值确认位置/yaw 连续驻留 3 仿真秒、之后 bridge ACTIVE 保持 600 仿真秒，并取得充分的 raw VIO / 地图净空 / 跟踪 / 时效 / 重规划证据及安全降落读回。guard 越线、planner 拒绝、样本失效均按现有取消/bridge 安全降落流程结束，不重试、不提高 guard、不缩短路线。一次运行只用于判别 #347 假设。

## 固定条件

- 单 D435i、Gazebo/PX4 SITL、`official_ego`、唯一 PX4 控制者为 `uav_px4_bridge`；真值只读评估。
- spawn `[-8,0,0.3,0,0,0]`；目标 `+16 m X / +0.10 m Z / +0.20 rad yaw`；1.0 m horizon；加速度 0.25 m/s²/axis；inflation 0.730617917 m。
- 0.12 m/s guard、健康/地图/接触/起飞/落地门和运行代码、安装版本固定。仅 planner `max_velocity_m_s` 从 #346 的 0.30 改为 0.25。
- 速度配置是样条可行性输入，不当作实飞速度；报告分别记录 planner 控制点导数、EGO reference、PX4 本地速度。

## 运行前核验

配置与 #346 除 planner `max_velocity_m_s` 及说明文字外，所有运行字段一致。代码、安装 binary 未变；复用 #344/#346 对同一源码的 405 unit tests、navigation-adapter integration 和 official-policy ROS probe，不重复运行无关测试。完整文件哈希在[机器可读协议](n10-horizon1-speed025-protocol-20261026-347.json)。

## 唯一运行命令

```bash
D435I_N08_MODE=execute \
D435I_N09_CONTACTS=1 \
D435I_PLANNER_CONFIG=config/components/mapping/n10_horizon1_speed025_calibration.json \
D435I_SPAWN_CONFIG=config/components/simulation/n10_long_range_spawn_minus8.json \
bash tools/project.sh sim n10-20261026-347-horizon1-speed025

docker exec d435i-n10-20261026-347-horizon1-speed025 \
  bash /workspace/tools/n09_runtime.sh \
  n10-20261026-347-horizon1-speed025 \
  config/components/navigation/n10_long_range_vio_calibration_goal.json \
  n10_calibration
```

结束后先独立确认 PX4 landed/disarmed、bridge LANDED/control disabled，再只停止本轮项目容器。
