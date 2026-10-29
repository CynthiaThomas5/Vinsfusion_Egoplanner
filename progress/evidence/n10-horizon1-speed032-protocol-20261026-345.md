# #345 N10.3：1 m 局部视野速度响应诊断协议

状态：**运行前冻结**。该诊断只测本地 EGO 规划视野对参考速度和重规划行为的影响；不会把全局 16 m 目标缩短，也不授予高于现有速度 guard 的运行资格。

## 假设与唯一变量

#344 使用 0.32 m/s/axis 使 EGO 发出同目标 B 样条，但 EGO 参考速度在 2.316 sim-s 后达到 `0.120142 m/s`，触发原 0.12 m/s guard。此时 PX4 实测峰值为 `0.085965 m/s`；取消停车样条随后因超出 N08 校准范围被拒，桥接器执行降落。

唯一主变量：`planning_horizon_m` 从 #344 的 `2.0 m` 降为 `1.0 m`。假设较短的局部规划距离可降低首段参考速度，并让 EGO 反复局部重规划继续朝相同全局 16 m 目标推进。这个关系尚未证实，所以只做一次新配置诊断。

## 固定项与判据

- spawn `[-8,0,0.3,0,0,0]`，单 D435i、`official_ego`；同一 +16 m X / +0.10 m Z / +0.20 rad yaw goal、0.25 m/s²/axis、0.730617917 m inflation。
- planner feasibility allowance 保持 `0.32 m/s/axis`；双源 reference/PX4 实测向量速度 guard 保持 `0.12 m/s`。健康、地图、障碍、接触、起降、到达和时间门限全部不变。
- 任一无效或越限速度样本均按现有逻辑取消并由 bridge 执行安全降落；不提高门限、不重试相同 profile。
- 即使未触发 guard，也只有在原生目标成功、独立 3 sim-s 到达驻留、600 sim-s active hold、足够长程 VIO/map/净空/跟踪/时效/重规划证据和安全末态齐全时，才支持长距离部分。

## 运行前检查

候选 `config/components/mapping/n10_horizon1_speed032_calibration.json` 与 #344 基线逐字段比较后，唯一运行字段差异应为规划视野 `2.0 → 1.0 m`；JSON 可解析。代码、安装和第三方补丁没有变化，所以复用 #344 的 405 unit tests、navigation-adapter integration 和 official-policy ROS probe 结果；不需要重复构建。输入哈希见 [机器可读协议](n10-horizon1-speed032-protocol-20261026-345.json)。

## 命令

```bash
D435I_N08_MODE=execute \
D435I_N09_CONTACTS=1 \
D435I_PLANNER_CONFIG=config/components/mapping/n10_horizon1_speed032_calibration.json \
D435I_SPAWN_CONFIG=config/components/simulation/n10_long_range_spawn_minus8.json \
bash tools/project.sh sim n10-20261026-345-horizon1-speed032

docker exec d435i-n10-20261026-345-horizon1-speed032 \
  bash /workspace/tools/n09_runtime.sh \
  n10-20261026-345-horizon1-speed032 \
  config/components/navigation/n10_long_range_vio_calibration_goal.json \
  n10_calibration
```

结束时须独立读回 PX4 landed/disarmed、bridge LANDED/control disabled，再停止本次项目容器。不得停止两个无关容器。
