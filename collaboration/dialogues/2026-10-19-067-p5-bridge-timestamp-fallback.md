# P5 bridge 时间戳回退修复与复测

- 用户要求继续 P5 SITL 诊断；不放宽 `COM_OF_LOSS_T=1.0`、VIO 质量门或 odometry 新鲜度门。PX4 控制仍由 `uav_px4_bridge` 独占，真值只交给独立只读 observer，不发送导航目标。
- #182 的 Offboard signal loss 与 bridge 输出中的一次时间戳回退吻合：回退值来自旧 `TimesyncStatus.timestamp`；按 ULog 中的 estimated offset 换算后比 PX4 HRT 旧1.024秒。
- 修改 bridge 的 mapper 失败回退为当前系统／Agent 时间；若 timesync 不新鲜则仍不发送控制时间戳。定向测试和独立 Jazzy colcon 包构建通过。
- #183 输出236条单调的 setpoint 时间戳，但起飞阶段定位适配器 `telemetry_stale`，bridge 因 external odometry 年龄0.372秒超过0.3秒上限而降落。车辆最终 landed/disarmed；90秒只读真值采集成功。该轮不算悬停。
- 下一步：检查 VINS estimator telemetry、优化里程计和 `/clock` 的源龄／接收间隔，保持所有既有门限。完整运行与哈希见 [`p5-vio-hover-timestamp-fallback-20261019-183.json`](../../progress/evidence/p5-vio-hover-timestamp-fallback-20261019-183.json)。
