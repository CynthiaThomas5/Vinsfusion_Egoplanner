# N06 continuous yaw pilot

- Goal completion mode继续N06；N06/S4仍in_progress，unknown fail-closed，PX4／bridge／controller／setpoint／flight不启动。
- r26以单次accel／cruise／decel连续运动完成2°nominal yaw，debug truth约2.0116°。Recorder期899条LocalizationStatus全部有效；MapStatus持续ready。
- 三张snapshot的epoch/map_id/frame一致，source age为0.102–0.152秒；前后status identity与ready稳定，wrong epoch／map_id拒绝检查通过。
- live planner probe source/fusion age约0.112／0.017秒；actual VINS body sphere查询1,809 unknown、397 free、0 occupied，goal因`full_curve_planning_failed`被拒，0条曲线。图中无控制节点或控制topic。
- 该结果支持连续低速2°scan维持health和map freshness，但不能作为N06入口；下一项r27把相同运动扩展到15°，观察覆盖能否减少unknown。配置：`config/components/simulation/n06_yaw_continuous_15deg_quarter_accel.json`。
