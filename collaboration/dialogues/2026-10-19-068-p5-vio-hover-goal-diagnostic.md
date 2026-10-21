# P5 悬停与小目标视觉闭环诊断（#184–#187）

用户要求继续推进 `GOAL.md`。本轮保持 P0–P6 既定范围；SITL 外的旧工程和设备不修改。真值只接独立只读 observer，PX4 控制仍由 `uav_px4_bridge` 独占；不调整定位、桥接或 PX4 的健康门限。

运行 #184、#185 为定位／PX4 freshness 的 run-local 诊断副本，只记录现有状态变化及时间年龄；两轮均未完成悬停。#186 的 no-goal 桥接 hold 完成 20.007 秒悬停，696 条轨迹设定点时间戳单调，最终 landed/disarmed。该轮首次质量锁发生在悬停结束后的降落阶段，不能代替导航目标。

#187 在无 GPS 的 VIO/EGO/PX4 组合下发送相对当前位置的小 3D+yaw 目标。Action 被接受并观察到209条匹配 READY 轨迹命令，但 `normalized_cost=1.37255` 后按既有 fail-closed 路径中止；PX4 最终 landed/disarmed，任务失败。90秒只读真值采集完成，单次固定 SE(3) 对齐的 flight-window 位置 RMSE/P95 为2.94/5.64 cm；门控时误差约3.08 cm。该 run 的分组 Ceres 代价中视觉组占89.1%，与 #180 接近，但单次关联不定位根因。PX4 ULog 记录 EV position/yaw 融合、GNSS position aiding 为零；降落阶段存在短暂 `failsafe=true` 与 `offboard_control_signal_lost`，所以不称为 failsafe-free。

证据和 SHA-256 见 [P5 运行证据 #184–#187](../../progress/evidence/p5-vio-hover-goal-diagnostic-20261019-184-187.json)。P5 仍进行中，目标未成功；下一步先查启动期 freshness 和 PX4 preflight 的独立冷启动波动，保留所有 fail-closed 门限。
