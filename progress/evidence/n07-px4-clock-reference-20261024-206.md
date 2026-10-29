# N07 #206：PX4 时间参考修复与离线复算

## 结论

PX4 遥测龄与控制时间戳的时间参考修复、`uav_px4_bridge` ROS 构建和历史轨迹复算通过。#206 本身未能通过 N05 支架扫描门禁，因此没有启动飞行。后续 #207 在 ground SITL 中取得 bridge HRT／ROS `/clock` 实时诊断读回。结合 #198/#200/#204 累计 hover 3/3，N07 限定出口现已通过；已通过悬停 run 未复测。

## 根因与改动

#203 首次 `px4_telemetry_stale` 发生在 wall elapsed 27.918 s。该时刻监视器最后收到的 ROS `/clock` 是 481.668 s（接收龄 222 ms），而 PX4 的本地位置／姿态遥测已到 HRT 481.864 s。旧判定把遥测看成领先 `/clock` 196 ms，超过原有 65 ms future 限值。PX4 GZ bridge 会以 Gazebo sim clock 更新 PX4 HRT（`external/PX4-Autopilot/src/modules/simulation/gz_bridge/GZBridge.cpp`）。

`px4_bridge_node.py` 现在从带已知时钟映射偏移的 `VehicleLocalPosition` 和 `VehicleAttitude` 时间戳恢复 PX4 HRT；当前时间取 PX4 HRT 与已映射 ROS `/clock` 中较新的有效值。遥测源龄和未启用 uXRCE DDS 时间同步时发出的控制时间戳都使用这一参考。原 `/clock` 活性／新鲜度门、PX4 源龄限制和 65 ms future 限值未改。

按 HRT 复算 #203 首次中止行，attitude 和 local_position 源龄为 0 ms，land_detected 为 16 ms，vehicle_status 为 68 ms，estimator_flags 为 864 ms；均在各自原有最大源龄范围内。该行的 false-future 判定消失。#203 随后另有 VIO odometry 停顿及 `external_odometry_stale`，它不由本次时钟修复解释。

## 验证

- `bash tools/project.sh build ros`：通过，17 个包完成（7.55 s）。
- 桥接节点源码语法编译：通过。
- 对保存的 #198、#200、#203、#204 `flight.json` 中 ACTIVE/TAKEOFF 遥测快照按新 HRT 参考离线复算，样本数依次为 442、445、185、446；PX4 源龄／未来龄超限样本均为 0。#203 的首次安全中止行另按上述数值复算。
- `python3 tools/project_status.py`：通过结构一致性检查；其结果不作为构建或 SITL 通过证据。
- `git diff --check` 和最终状态／里程碑 JSON 检查：收尾时复核。

## 在线验证尝试 #206

冷启动 #206 使用未武装支架扫描 profile `n06_full_airframe_retreat_240_oblique_separated_return`。扫描完成 7/12 阶段后以 `normalized_cost_exceeded`（1.3045146）失败；post-release N05 gate 未完成，飞行器未进入飞行，没有启动 no-goal hover、airborne graph observer 或独立悬停 evaluator，因此该 run 不产生 N07 hover 通过记录。

`vio.log` 确认桥接节点启动并保持 `DISABLED`。本次没有保存 `/uav_px4_bridge/status/detail` 诊断流，所以没有可引用的 live HRT／ROS clock gap 读回；#206 不能算在线时间参考验证。

原始机器结果在 [`fixture-result.json`](../../artifacts/runs/n07-20261024-206-01/fixture-result.json)，阶段和 VIO 原始记录在同目录。收尾读回确认落地、未武装、支架已脱离且模型从场景移除；容器 `d435i-n07-20261024-206-01` 以 exit code 0 停止。未触碰其他容器。

## N07 状态与下一步

用户已将三次独立冷启动标准改为累计、不要求连续，并要求已通过项不复测。#198、#200、#204 均满足相同固定 runtime／runtime-contract、各自不少于 30 仿真秒无目标悬停及其他原有验收项，累计为 **3/3**；不重跑这些 run，不降低任何单次门限。#203 和 #206 都不清除已通过计数。

后续 #207 的地面在线读回证明新 bridge 在 PX4 时间域和 ROS `/clock` 正常推进时发布预期诊断字段；#203 中 196 ms ROS clock 接收滞后的特定事件由同一数据的离线复算覆盖。#207 未武装、未起飞，不增加 hover 次数。下一主线为 N08。详细记录见[改动记录](../changes/2026-10-24-206-px4-clock-reference.md)、[地面读回](n07-px4-clock-live-ground-20261024-207.md)和[对话摘要](../../collaboration/dialogues/2026-10-24-206-px4-clock-reference.md)。
