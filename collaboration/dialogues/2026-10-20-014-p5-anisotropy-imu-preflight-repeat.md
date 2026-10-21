# P5 横移复测前置门失锁与 IMU 观测 #220

日期：2026-10-20

## 任务摘要

- 在 #219 action 成功后使用完全相同的 #192 0.30 m/+30°目标、run-local filter 阈值0.01和只读 IMU 采集器，换 ROS domain/Gazebo partition 做独立冷启动。
- 本轮在目标派发前由定位健康门失锁；保留失败，检查 VINS 遥测、定位输出、PX4 ULog 和 IMU。
- 未订阅真值；没有启动控制阶段，不修改健康/PX4门限。

## 已确认

- 六包构建完成，动作前置条件整体曾为 true，但定位 TRACKING 稳定窗与 PX4 遥测稳定窗均未通过；action goal 未发送，bridge一直DISABLED、PX4保持disarmed。
- 定位最后一个有效状态在source stamp 12.404 s；12.648 s以optimized_stale无效，accepted optimized计数停在59、good_pairs为68。VINS telemetry继续更新至48.316 s，末样solver_usable、solve_current为true，normalized_cost=0.0282、long_tracks=36。
- IMU观察器保存12,213条约200 Hz样本，stamp单调、最大gap8 ms，shutdown时仍发现d435i_sensor_bridge发布者。
- ULog显示无dropout、GNSS aiding全零、7/76个样本记录EV position/yaw/velocity融合；没有Offboard/解锁，最终仍landed/disarmed。
- run-local图像观察器在ROS teardown时抛出ExternalShutdownException，没有图像manifest；本轮没有cost越线或目标，观察器异常不是导航失败原因。

## 解释边界与下一步

定位适配器报告optimized_stale，而VINS telemetry与IMU流继续。这说明输出健康链在目标派发前中断，但本轮没有直接采集原始VINS odometry话题，无法分辨VINS optimized odometry发布停止与适配器配对/接受问题。下一轮在新domain/partition复现同一配置，并加一个只读、低带宽的原始VINS odometry记录器，记录发布者身份、source stamp和接收时刻；继续保持所有门限。
