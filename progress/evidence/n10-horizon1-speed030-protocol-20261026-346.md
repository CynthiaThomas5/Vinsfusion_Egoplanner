# #346 N10.3：planner 0.30 m/s 与参考速度响应诊断协议

状态：**运行前冻结**。本次在已经测过的 1 m 局部视野下，只降低 EGO 的逐轴曲线可行性上限；16 m 全局目标、0.12 m/s guard 和全部其他门槛保持原样。该 planner 参数不是实际飞行速度。

## 假设与定量依据

#345 的第一条 B 样条实测 x 导数控制点最大值为 `0.328734 m/s`；`max_velocity_m_s=0.32` 对应 5% 每轴可行门 `0.336 m/s`。运行时 EGO reference 峰值 `0.123444 m/s`，触发既有 0.12 m/s guard。

唯一变量：`max_velocity_m_s` 从 `0.32` 降至 `0.30 m/s/axis`；horizon 固定 `1.0 m`。新可行门为 `0.315 m/s`，比 #345 实测 x 导数控制点低 `0.013734 m/s`，会要求样条时间重分配。若速度按重分配比例反比缩放，预期曲线时间增加约 `4.36%`、reference 峰值约 `0.1183 m/s`。这是明确待检验推断，不是保证。

## 固定项与判据

- 单 D435i、`official_ego`；spawn `[-8,0,0.3,0,0,0]`，同一全局 `+16 m X / +0.10 m Z / +0.20 rad yaw` goal。
- `planning_horizon_m=1.0`、最大逐轴加速度 `0.25 m/s²`、inflation `0.730617917 m`、EGO/ PX4 双源向量速度 guard `0.12 m/s` 固定。健康、地图、障碍、接触、起飞、到达和 PX4 落地门均不变。
- 若 planner 拒绝，完整保留拒绝原因；若速度 guard 越限或样本无效，按现有取消和桥接器降落逻辑结束。不能为了完成路线提高阈值或缩短目标。
- 即使本次未越限，只有原生目标成功、独立 3 sim-s 到达驻留、600 sim-s active hold、长程定位/map/净空/跟踪/时效/重规划证据和安全末态全部满足，才支持相应校准出口。

## 运行前核验

候选配置 `config/components/mapping/n10_horizon1_speed030_calibration.json` 与 #345 的 1 m 配置逐字段比较，唯一运行差异应为 `max_velocity_m_s: 0.32 → 0.30`。JSON 与输入 SHA-256 在 [机器可读协议](n10-horizon1-speed030-protocol-20261026-346.json)。源代码和安装不变，复用 #344 的 405 unit tests、navigation-adapter integration、official-policy ROS probe。

## 运行命令

```bash
D435I_N08_MODE=execute \
D435I_N09_CONTACTS=1 \
D435I_PLANNER_CONFIG=config/components/mapping/n10_horizon1_speed030_calibration.json \
D435I_SPAWN_CONFIG=config/components/simulation/n10_long_range_spawn_minus8.json \
bash tools/project.sh sim n10-20261026-346-horizon1-speed030

docker exec d435i-n10-20261026-346-horizon1-speed030 \
  bash /workspace/tools/n09_runtime.sh \
  n10-20261026-346-horizon1-speed030 \
  config/components/navigation/n10_long_range_vio_calibration_goal.json \
  n10_calibration
```

运行后先独立确认 PX4 landed/disarmed、bridge LANDED/control disabled，再只停止该项目容器。
