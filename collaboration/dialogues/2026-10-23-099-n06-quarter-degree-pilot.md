# N06 quarter-degree pilot

- Goal completion mode继续N06，范围和原验收出口不变；unknown fail-closed，PX4／bridge／controller／setpoint／flight不启动。
- r24执行8个0.25°rest-to-rest yaw步进，每步静止约5.164秒。Mapping health gate在sim29.668s关闭，truth yaw约1.199°，IMU积分约1.198621°；首条invalid LocalizationStatus在sim29.751s／truth yaw约1.209°，reason=`normalized_cost_exceeded`。
- 三个hold的VINS特征计数中位数依次约109、112、114；gate附近计数曾为2／3，随后恢复。VINS在sim29.668s估计yaw约2.310°，与truth约差1.11°。MapStatus从sim29.854s起为`input_ready=false`／`map_reset_acknowledged`，之后持续未恢复。
- input recorder完成约91.128s窗口；深度header 2,670条、采样forwarded depth／精确pose 770帧、optimized odometry385条。motion truth实际累计约2.727°，高于命令2°。snapshot-01 readiness超时，runner exit1，已确认容器及匹配进程停止。
- 下一实验只把角加速度降四倍，保持0.25°步长、2°总量、hold、位置和surround。profile为`config/components/simulation/n06_yaw_microstep_025deg_quarter_accel.json`；下一run `n06-20261023-wall-r25`。
- N06/S4仍`in_progress`，next_goal仍N06；r25通过pilot也不等于全周观测或N06通过。
