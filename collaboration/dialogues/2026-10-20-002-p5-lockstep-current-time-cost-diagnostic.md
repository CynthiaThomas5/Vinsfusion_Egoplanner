# P5 lockstep 当前时间戳与视觉代价诊断（#199–#202）

## 本轮目标

继续无真值 VIO→PX4→EGO 零偏移 SITL 诊断，查明 #199 的 PX4 当前控制时间戳拒绝，并保留首次 normalized-cost 越线时的 VINS 分组代价。遵守单 D435i 仿真边界，PX4 控制仍由 `uav_px4_bridge` 独占；不使用在线真值，不放宽 PX4 freshness、65 ms future 容差或 `normalized_cost=1.0`。

## 决定

- #199 的 `clock_mapping_rate_out_of_bounds` 发生在 TAKEOFF、goal 发送前。当前 Offboard 时间戳在 `UXRCE_DDS_SYNCT=0` 的 Gazebo lockstep 组合中应直接取最新 `/clock`/PX4-HRT 样本，不应依赖历史墙钟/仿真时钟速率拟合。
- direct-current path 仍须有足够样本、时间 mapper 未锁定、接收时刻不回退且样本新鲜。历史 VIO source-stamp 转换及其 rate/freshness checks 保持不变。
- #200 与 #202 用有效 ROS domain 和 run-local install 复核；#201 的 domain 233 超出 Fast DDS 端口范围，分类为无效轮次，不作为系统失败。
- #202 保留一次 VINS 分组 Ceres cost：visual 82.589%、marginalization 17.025%、IMU 0.387%。没有特征级残差或可确认根因，因此不改质量门。

## 结果

- #199：PX4 bridge 报 `clock_mapping_rate_out_of_bounds`，未发送 action goal，最终 landed/disarmed。
- #200、#202：没有 `px4_timestamp_error`，通过 Offboard/takeoff 并发出目标；两次都由现有 `normalized_cost > 1.0` 门安全中止并落地解除武装。
- #202：目标首次越线 normalized cost 为 1.00468；VINS 输入/双目特征与 long-track 数未同步骤降，双目图像 stamp skew 为 0，tracker 时长约 7.193 ms。
- #202 ULog：EKF2 EV position/yaw/velocity flags 各在 22/39 个样本为 true，GNSS aiding flags 均为 0/39；无 ULog dropout，电池 warning/fault 为零。触地后约 0.72 仿真秒出现短暂 DESCEND/failsafe，之后 disarm。

## 待决

视觉组占比最高，但当前分组只到视觉因子整体，不能定位坏特征、图像区域或真实场景原因。下一步分析逐特征残差/图像对应关系，并保留只读评估隔离；目标完成前仍需 P4–P6 与 A–H 全部实际验收。

结果证据仅在 [轻量验收报告](../../progress/evidence/p5-px4-lockstep-current-time-cost-diagnostic-20261020-199-202.json)；本对话摘要不作为测试通过依据。
