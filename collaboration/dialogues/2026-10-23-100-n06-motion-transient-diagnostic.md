# N06 motion-transient diagnostic

- Goal completion mode继续N06，用户范围和出口不变；PX4／bridge／controller／setpoint／flight均不启动。
- r25仅将0.25°步进角加速度降四倍，仍在truth yaw约0.927°的gate event触发`normalized_cost_exceeded`；首条invalid status于sim34.060s／truth yaw0.938°。
- 通过live transient-local status读到首次锁存`normalized_cost=1.0423633`，上限1.0，source stamp约34.012s；`good_pairs=504`。IMU积分与truth只差0.000143°，VINS姿态约高0.705°。Gate后特征计数仍可短时超过100，特征可见不代表健康。
- MapStatus后续`input_ready=false`／`map_reset_acknowledged`。motion truth、105秒输入记录完成；snapshot在120秒ready wait后超时，无snapshot。容器／进程停止，exit code未捕获。
- 下一轮r26只移除重复start/stop：保持角加速度、peak rate、2°总角、wall场景，改为一次加速、连续匀速、一次减速。profile为`config/components/simulation/n06_yaw_continuous_2deg_quarter_accel_pilot.json`。
- N06/S4仍`in_progress`，next_goal仍N06；r26 pilot通过也不等于full-turn coverage或N06完成。
