# 对话摘要：N07 PX4 时间参考地面集成读回

- 用户要求先处理 PX4 时间戳与 ROS 时钟滞后，并将 N07 次数要求改为累计、不要求连续；已通过 run 不复测。
- #206 修复 PX4 HRT 与映射 `/clock` 的年龄／控制时间戳参考，保留原活性门和所有门限。构建与 #198/#200/#203/#204 离线复算通过。
- #206 N05 地面扫描第 7/12 阶段 `normalized_cost_exceeded`，未进入飞行；已安全落地、支架移除、容器停止。
- #207 另启地面 SITL，桥接器保持 DISABLED；在线读取 `px4_time_reference_us`、clock gap、clock 回调龄和 PX4 各源龄。PX4 时间域有效、clock gap 0、源龄均在原限值内。未武装、未起飞、未计为 hover run。
- 已通过的 #198/#200/#204 保持 3/3，不复测；N07 限定出口通过，下一主线指针更新为 N08，但本轮没有执行 N08。
- #203 的 VIO odometry stall 和 `external_odometry_stale` 仍独立记录，不归因于 PX4 时间参考修复。
