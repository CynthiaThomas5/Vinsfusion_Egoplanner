# N06.4 r24 0.25° microstep pilot

日期：2026-10-23。Goal 完成模式，范围 N06。父目标 N06/S4 保持 `in_progress`。

## r24 结果

r24 在 wall textured surround、固定位置下执行 8×0.25° rest-to-rest yaw 步进，每步静置约5.164秒，角加速度为 `0.0104719755 rad/s²`。第三个hold期间 VINS 特征计数中位数为114、范围2–116；第四个step于sim29.464s开始。Mapping health gate 于sim29.668s关闭，原因`normalized_cost_exceeded`；debug truth yaw为1.199°，IMU z积分yaw为1.198621°。首条invalid LocalizationStatus在sim29.751s，此时truth yaw约1.209°。VINS log在sim29.668s估计yaw约2.310°，比truth高约1.11°。MapStatus在sim29.854s转为`input_ready=false`／`map_reset_acknowledged`，随后整段记录未恢复。

gate前一帧的VINS `n_pts`为116／115，gate附近短暂降到2／3，下一时间点回升到115／43；计数回升没有解除定位锁存。因此 r24 不支持“单纯把最大连续角度降至0.25°即可维持定位健康”。角速度计积分与truth一致，但VINS姿态偏离truth，值得在下一轮区分运动瞬态与视觉惯性估计关系。

motion truth记录5,667条truth与14,167条IMU，clock为sim 5.057–61.724s；指令总角2°，debug truth累计约2.727°。90秒input窗口实际91.128秒，保存2,670条raw depth header、770组转发depth/精确camera pose、385条optimized odometry；forwarded depth最后stamp为sim29.602s。snapshot-01按120秒MapStatus readiness等待后失败，提示`map_reset_acknowledged`，没有快照。runner以exit 1结束，容器与匹配项目进程均停止。数据和SHA-256见[机器报告](n06-yaw-microstep-reacquisition-20261023-099.json)及[运行目录](../../artifacts/runs/n06-20261023-wall-r24/)。

## 下一项：r25 四分之一角加速度

只改变角加速度：从`0.0104719755`降至`0.0026179939 rad/s²`。保留0.25° step、2° nominal total、每步5.164秒静置、同一wall场景和位置。更长加减速phase使峰值角速度随之减半。该假设针对r24“特征大部分时间较多、IMU积分与truth一致，但VINS估计明显偏离并触发normalized cost”的组合证据。

profile：[n06_yaw_microstep_025deg_quarter_accel.json](../../config/components/simulation/n06_yaw_microstep_025deg_quarter_accel.json)。

```bash
bash tools/run_n04_map_layout.sh n06-20261023-wall-r25 wall_box_column 88 motion_n06 config/components/simulation/n06_yaw_microstep_025deg_quarter_accel.json
```

pilot成功标准为LocalizationStatus有效至至少1.5°实际truth yaw、MapStatus保持同一epoch/map identity且depth新鲜，并捕获匹配snapshot。pilot成功只支持后续observation scan，不代表full-turn coverage或N06通过；原N06.2两布局曲线、hold、handoff和故障拒绝出口均保持未通过。
