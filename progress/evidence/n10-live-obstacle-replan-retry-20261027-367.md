# N10.3/#367 动态障碍重规划诊断结果

## 结论

**失败，保留为诊断证据，不计 N10 或 N12 通过。** Gazebo 在目标开始后 12.008s 确认创建方箱；D435i/EGO occupancy 表面观测到该障碍，同一 goal/epoch 在注入后继续产生轨迹（首个替代 traj_id=25，记录到 290）。实际飞行箱体净空离线采样下界为 0.982m、禁碰撞接触为 0。

导航动作以 `goal_timeout` 结束，墙钟 360.1s / 仿真 317.968s；真实目标未到达。PX4 bridge 在仿真 129.264s 因 `external_odometry_stale` 进入 LANDING。

## 已查明的直接原因

在 bridge 进入 LANDING 时，最新成功映射的里程计已有 0.345s。定位源时间线显示一个 VIO 样本时间为 128.968s，而当前 ROS 仿真时钟为 129.264s，晚到 0.296s；该样本仍在配置的 0.35s source-age 内，但映射器只保存64个 `/clock` 样本（约0.256s仿真跨度），报 `source_stamp_outside_clock_history`，没有将样本发给 PX4。随后映射后里程计龄超过0.3s，bridge 执行降落。定位状态当时仍为 TRACKING/valid，EGO 没有因 planner failure 中止。

因此 N10.3 后续唯一变量定为把 `clock_mapping_max_samples` 64 改为128；不放宽0.35s源龄、0.3s接收龄或PX4控制条件。#368复测协议已冻结。

## 净空与末态

- 动态方箱：中心 (0,0,1.4)m，尺寸0.8×0.8×2.8m；create ACK与表面occupancy观测均通过。
- 全机包络对方箱：采样最小 1.002m，扣除观测到的样本间包络位移 0.020m 后为 0.982m。全世界相同方法调整后为 0.205m；均不是连续动力学证明。
- 禁止接触0。独立postflight读回确认LANDED、disarmed、control disabled、zero control；`safe-to-stop.json=true`；项目容器已退出。
- 到达评估报告 `landed_and_disarmed=false` 是飞行runner失败分支未记录外部已完成降落字段所致，不能覆盖独立读回。VIO误差评估因该run没有完整flight record而未产出，仍待合格样本覆盖。

## 产物

完整数据：`artifacts/runs/n10-20261027-367-ego-retry-live-obstacle/`。运行分析器 SHA-256：`c12ae0e111e98046d6f0c0774167a476523953a51408ec0e06240c2265098f73`。协议与预启动身份见[#367冻结协议](n10-live-obstacle-replan-retry-protocol-20261027-367.md)和[#367 prelaunch](n10-live-obstacle-replan-retry-prelaunch-20261027-367.json)。结构化结果见[JSON](n10-live-obstacle-replan-retry-20261027-367.json)。
