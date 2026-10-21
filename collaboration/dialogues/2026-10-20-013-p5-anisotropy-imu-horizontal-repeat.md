# P5 横移目标与直接 IMU 输入复测 #219

日期：2026-10-20

## 任务摘要

- 在 #218 修复 run-local 只读 IMU 观察器的信号收尾后，以 #192 的目标配置复跑横移 0.30 m、yaw +30°，保持 feature anisotropy 阈值 0.01、全部定位与 PX4 门限。
- 在 /sensors/d435i/imu 记录原始 source stamp、加速度和角速度；不订阅真值、不发布控制。
- 对齐 IMU、VINS 首次质量越线、定位锁定和 PX4 着陆状态，判断 #214/#215 的加速度偏置事件是否重现。

## 决定与结果

- #219 冷启动动作成功，桥接与 PX4 最终报告 landed/disarmed。accel_bias_norm 峰值 0.133932 m/s²，低于现有 0.15 门限。
- 后续 normalized_cost 在 source stamp 31.188 s 首次达到 1.0261；31.252 s 定位以 normalized_cost_exceeded 进入 invalid，发生在 bridge 已开始 LANDING 之后。
- 记录到 12,619 条约 200 Hz IMU 输入。最大加速度范数 143.72 m/s² 出现在 31.088 s，约提前 100 ms 于首次 cost 越线；PX4 sensor_combined 同一时刻也记录大幅冲击。PX4 本地位置随后接近地面并减速。该时间关系与降落冲击相符，但单次 run 不证明因果。
- 首次 cost 越线帧有 757 个视觉 residual block；双目配对时间差为零。大残差空间上远离拟合强边缘，且残差特征未发现 ratio<0.01；单帧图像诊断不能定位根因。
- 0008 仍仅供 run-local 诊断。P5 未通过；无健康门限、PX4 参数或控制行为变化。

## 用户约束

按项目 AGENTS 约定保留用户已有修改；只推进 P0–P6；真值不进入最终 VIO 组合；PX4 控制发布者唯一；不改只读来源；不推送。源文件与运行产物采用 run-local 哈希清单，失败与诊断证据保留。

## 待决与下一步

- 用新 ROS domain 与 Gazebo partition 重复同一横移目标和只读 IMU 采集，比较动作结果、LANDING 中 cost 越线以及 IMU 冲击是否复现。
- 保持阈值和所有安全门不变；本次及下一次都不作为 D/E/F 正式验收。
