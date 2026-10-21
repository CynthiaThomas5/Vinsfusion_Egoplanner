# P5 PX4 Timesync observed/estimated offset 对照

- 用户要求继续整个项目目标；本轮只增加只读 `observed_offset` 采样并运行被动SITL，没有发布控制、调用enable、解锁或飞行。
- #111使用新domain/partition/build副本运行45秒：VIO送达PX4 277条，EV position/yaw融合，GNSS flags全零，无truth/控制并保持disarmed。
- 35/345条 `px4_telemetry_stale` 位于estimated_offset变化窗口13.755–19.228秒及末次变化后68ms；之后25.72秒无stale。窗口内attitude/local-position未来戳174/1812、90/907；估计值末次变化后年龄P95 4.746/8.874ms。
- `observed_offset`继续按−0.5804秒/墙秒变化，/clock为0.4196仿真秒/墙秒。estimated_offset从19.228秒保持不变，observed_offset后来又变化约−13.98秒，表明“估计字段不变”不等于timesync收敛。PX4滤波器高偏差重置代码路径吻合该模式，但运行未记录内部reset counter。
- 证据：[progress/evidence/p5-px4-observed-offset-diagnostic-20261017-111.json](../../progress/evidence/p5-px4-observed-offset-diagnostic-20261017-111.json)。随后 #112 扩展到75秒检查重复性。当前readiness仍因DISABLED下preflight失败为0，P5未通过。
