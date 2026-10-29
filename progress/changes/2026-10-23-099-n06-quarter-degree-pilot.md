# 2026-10-23 #099 N06 quarter-degree pilot

对话摘要：[N06 quarter-degree pilot](../../collaboration/dialogues/2026-10-23-099-n06-quarter-degree-pilot.md)

## 结果与记录

- r24 把最大不间断角度降到0.25°并保持每步5.164秒静置，但sim29.668s／truth yaw1.199°仍触发`normalized_cost_exceeded`；首条invalid status为sim29.751s／truth yaw1.209°。其后MapStatus保持`map_reset_acknowledged`，snapshot readiness超时，run exit1。
- 三段hold的`n_pts`中位数为109、112、114；gate附近计数短暂降为2／3再回升。IMU z积分与truth yaw几乎一致，VINS估计yaw则约2.31°，比truth高约1.11°。
- input recorder 90秒窗口完整落盘，motion truth完整落盘；结束时项目容器和匹配进程已停止。原始哈希与复算值见[#099机器报告](../evidence/n06-yaw-microstep-reacquisition-20261023-099.json)。
- 新增 `n06_yaw_microstep_025deg_quarter_accel.json`，保持step／hold／总角度／场景，仅将角加速度降四倍。r25尚未运行。
- 更新 CURRENT、GOAL、执行书、里程碑和N06主报告为r25唯一下一子项；N06/S4及原验收阈值保持不变。

## 验证

- profile复算：8×0.25° nominal=2°；每步phase为`2×1.290994 s`加`4×1.290994 s`静置；角加速度`0.0026179939 rad/s²`；峰值角速度约`0.00337982 rad/s`。
- r24 `bash tools/run_n04_map_layout.sh ...`：runner exit 1；snapshot client报告MapStatus在120秒内未ready，`map_reset_acknowledged`。无残留项目container/process。
- 状态写回后运行`python3 tools/project_status.py`、profile/static consistency check、`git diff --check`与`git status --short --branch`。结构检查不代替N06正向出口。

## 限制与下一步

r24说明较小step与静止hold不足以保持VINS健康；尚未归因normalized-cost锁存。下一步在保持其他量不变时降低角加速度，检查VINS/truth差异和地图ready能否改善。PX4、bridge、controller、setpoint和flight均不启动。
