# N07 #207：PX4 时间参考地面 SITL 集成读回

## 结果

**时间参考集成读回通过；不构成飞行或 hover 验收。** 在新启动的 headless ground SITL 中，桥接节点使用本轮构建的 `px4_bridge_node.py`。节点保持 `DISABLED`，没有请求武装或起飞。

`/uav_px4_bridge/status/detail` 的在线读回为：`px4_time_domain_valid=true`、PX4 时间参考 `31420000 us`、映射 ROS `/clock` 与 HRT 差 `0.0 s`、clock 收到／推进龄约 `0.0031 s`。attitude、estimator_flags、land_detected、local_position、vehicle_status 源龄分别为 0、0.268、0.164、0.012、0.472 s，均在原有源龄和 future 门限内。

桥接器状态为 `DISABLED`，原因字段是 `px4_preflight_failed`。此次检查只验证 PX4 HRT、ROS clock 映射和诊断字段在实际地面 SITL 中接通；它不表示飞行前置通过，也没有复现 #203 的 196 ms clock 接收滞后。延迟情形由 #203 离线复算覆盖。

## 收尾

`bash tools/project.sh stop n07-20261024-207-clock-ground` 返回 0；容器退出码 0、`OOMKilled=false`，停止后活动项目容器数为 0。没有运行 control service、fixture、goal 或 observer。

机器可读读回和哈希见[JSON 报告](n07-px4-clock-live-ground-20261024-207.json)及[原始 run 记录](../../artifacts/runs/n07-20261024-207-clock-ground/px4-clock-ground-readback.json)。

## N07 交接

N07 三次 hover 仍由 #198、#200、#204 支持，累计 3/3；不连续要求已按用户指令移除，且这些通过 run 没有复测。PX4 时间参考问题已由构建、四次历史轨迹离线复算和本次 ground SITL 读回验证。#206 的 N05 扫描失败和 #203 另一个 VIO odometry stall 均保留为失败／独立问题，不清除通过次数。N07 限定出口通过；整体 GOAL 仍继续后续主线任务。
