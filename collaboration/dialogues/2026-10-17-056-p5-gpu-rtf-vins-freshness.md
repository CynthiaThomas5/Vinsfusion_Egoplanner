# P5 GPU RTF 与 VINS freshness 复测

- 用户目标仍为完成 `GOAL.md` P0–P6 与 A–H；本轮运行本地被动 SITL，不改项目源码、相机规格、健康门限或PX4 offset滤波器。所有成功运行保持 DISABLED、disarmed、零控制、无truth。
- #122–#125确认 RTX 3060 可经 NVIDIA EGL 使用。GPU map/EGO profile RTF约0.66，GPU VINS/localization RTF约0.81；同类CPU-only约0.37/#121和0.42/#114。GPU采样显示有活动，但observed_offset仍与RTF互补漂移。
- GPU负载下仍有freshness失锁：#123短暂产生40组同stamp地图输入与1,188个占据点，随后定位报`propagated_from_future`；#124完整导航profile在目标前`telemetry_stale`锁定，无goal/map/VIO；#125未等raw VINS准备就启动adapter，立即telemetry_stale。
- #126 run-private warmup helper因属性赋值错误退出；#127修正后按现有`health.json`限值等待10组原始VINS配对，约4.06秒后通过。定位短暂TRACKING后因VINS `imu_propagate` 收包间隙0.337秒转LOCKED/`propagated_stale`；PX4收到28条VIO但未见EV融合。
- GPU提高Gazebo吞吐，但没有解决VINS到定位的新鲜度长尾与PX4融合。下一步需要对齐原始VINS publish、定位 take、源戳/收包时间和进程时间线；P5未通过。
