# N06.4 r25 四分之一角加速度 pilot

日期：2026-10-23。Goal 完成模式，范围 N06。父目标 N06/S4 保持 `in_progress`。

## r25 结果

r25 保留0.25°步进、每步约5.164秒静态hold、2°命令总角、位置与wall surround，仅把角加速度降四倍至`0.0026179939 rad/s²`。尽管较慢，mapping health gate仍在sim33.958s／truth yaw0.927°关闭；首条invalid LocalizationStatus在sim34.060s／truth yaw0.938°，原因`normalized_cost_exceeded`。IMU z积分yaw在gate时为0.927047°，与debug truth相差约0.000143°；VINS估计yaw约1.632°，高于truth约0.705°。

运行容器仍在snapshot readiness等待时，读取了transient-local LocalizationStatus的锁存值：`normalized_cost=1.0423633`，超过未更改的`max_normalized_cost=1.0`。状态记录该cost源stamp为sim34.012s，`good_pairs=504`；健康锁存后status不会自行恢复。后续单次原始estimator telemetry样本是在继续运动很久之后取得，cost约1.7146、solver flags均为true；它是post-lock观察，不能当作首次越线原因。运行时特征在gate附近仍超过100，说明不能仅凭特征数判断quality通过。

MapStatus在sim34.115s转为`input_ready=false`／`map_reset_acknowledged`并持续未恢复。motion truth有6,701条truth、16,752条IMU，实际累计2.887°；105秒input窗口实际106.329秒，包含3,108条raw depth header、900组转发depth/精确camera pose和450条optimized odometry。snapshot-01 readiness等待120秒后超时，无snapshot；已确认项目容器和匹配进程停止，但host exec session丢失后runner exit code未保存。结构化数值及哈希见[机器报告](n06-yaw-motion-transient-20261023-100.json)与[运行目录](../../artifacts/runs/n06-20261023-wall-r25/)。

## 下一项：r26 连续低速转向

r23–r25 的分段起停都在较小truth yaw处锁存；r21连续慢转的估计姿态则持续到约16°才锁存，但没有motion truth文件。r26只改变运动形式：用一次加速、七个零角加速度匀速phase、一次减速，保留r25角加速度、峰值速率、2°命令总角、wall位置与surround，并保留起始及末端静止段。profile中的匀速phase保持当前角速度，不是静止hold。

profile：[n06_yaw_continuous_2deg_quarter_accel_pilot.json](../../config/components/simulation/n06_yaw_continuous_2deg_quarter_accel_pilot.json)。

```bash
bash tools/run_n04_map_layout.sh n06-20261023-wall-r26 wall_box_column 89 motion_n06 config/components/simulation/n06_yaw_continuous_2deg_quarter_accel_pilot.json
```

pilot成功标准为健康状态有效至至少1.5°实际truth yaw、MapStatus保持相同epoch/map identity且depth新鲜，并捕获匹配snapshot。成功仍不构成全周覆盖或N06通过；N06.2两布局实际曲线、hold、handoff与故障拒绝出口均未满足。
