# N08 #313：低位后向扫描在组合 yaw/pitch 转动中被健康门拒绝

状态：未通过；未进入 fixture release N05 或 N08 mission。

## 试验假设和结果

#313 profile 保留 #312 的前 10 阶段和原阈值，把 z=1→0.5→0 m 回收移到后向观察前；最后在 z=0、yaw=−π、pitch=−0.35 rad 做后向观察，再回到 yaw=0。

新冷启动中，垂直回收及 z=0 的 yaw=0 静止段完成，没有复现 #307/#312 在 z≈0.8–0.9 m 的下降锁存。第 14 阶段（0-based index 13）同时从 yaw=−π/2 转向 −π、并从 pitch=0 上仰至 −0.35 rad；在仿真 439.948 s、实际 yaw≈−2.121 rad/pitch≈−0.230 rad 时，health gate 以 normalized cost=1.022129>1.0 锁存。前一条 fixture trace 仍有效，cost=0.944185。`stale_observation=null`，optimized/telemetry 源龄约 120/56 ms，prior evaluation 与 spectrum 均通过；cost 组：marginalization 1066.91/82、visual 306.89/2408、IMU 5.27/150 residuals。

这次结果支持“先下降”避开原下降时的健康拒绝，但没有完成后向观察。低位 yaw 和 pitch 同时运动的阶段触发锁存；还不能据此断言哪个轴单独导致 cost 上升。#314 将保持相同低位视角和下降顺序，只把 pitch−0.35 rad 的调整与 yaw 转动拆成不同阶段。

## 准入和安全末态

初始 N05 baseline 因 `ground_plane_insufficient_raw_occupied_voxels` 被 online/offline 一致拒绝。支架扫描完成 13/17 阶段后失败，fixture 已 detach，Gazebo model list 无 fixture，LandDetector 确认 landed。没有 post-release N05、40 s preflight、N08 几何检查或 mission；没有 goal、enable、PX4 控制或飞行。

独立 6 s readback：bridge `DISABLED/control_enabled=false/armed=false/landed=true`，PX4 `arming_state=1`、landed=true；OffboardControlMode、TrajectorySetpoint、VehicleCommand 均为 0。只停止 #313，容器退出码 0；其他容器未触碰。

机器摘要：[JSON](n08-low-rear-view-lockout-20261026-313.json)。静态 profile 证据：[配置报告](n08-low-rear-view-profile-20261026-313.md)。原始运行：`artifacts/runs/n08-cancel-highspeed-prescan-20261026-313/`。
