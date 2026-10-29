# N08 #311：rear scan 在回程早段被定位健康门中止

状态：没有 post-release N05，也没有 N08 mission。#311 的新 12 秒下降段未执行，因扫描器在第 7/17 阶段、回程初段被既有健康门中止。

## 时序结果

- 新 profile 使用 rear-facing short-hold 观察路线；支架扫描前 N05 baseline 因 `ground_plane_insufficient_raw_occupied_voxels` 拒绝，随后执行未解锁支持扫描。
- 第 7 阶段从 x≈−1.2 m 返回原点，VINS 在 sim 292.876 s 的优化样本触发 lockout；health snapshot 时间 293.008 s，normalized cost=1.048986 > 原限值 1.0。最后轨迹样本 x≈−0.985 m，x 轴速度≈0.0344 m/s。
- 该样本有 180 输入特征、172 stereo features、179 continued tracks，accel bias=0.04144 m/s²、gyro bias=0.0000708 rad/s。视觉组 cost=2389.14/4808 residuals；IMU=4.45/105；marginalization=354.59/82。末端 cost 主要由视觉 residual 上升构成。
- 唯一新 profile 变量位于阶段 14（回中后的下降 8→12 s）；本次只完成到阶段 7，因此不能评价这个变量。
- 对照：#309 同一侧视路线在第 7 阶段较靠近 x≈−0.46 m 时 cost=1.094；#310 同一路线通过该段，trace max=0.9531。#311 在 x≈−0.985 m 又出现 cost=1.049。当前数据支持这段返回的健康尖峰具有启动间变化，尚不能确认是固定空间点触发。

## 安全末态

fixture 已 detach 且 Gazebo 模型确认移除。独立读回为 PX4 `DISARMED/landed/at_rest`，bridge `DISABLED/control_enabled=false/armed=false/landed=true`。没有 post-release gate、goal、enable 或起飞。只停止本 run 的容器，停止命令及容器退出码均为 0。

机器摘要：[JSON](n08-rear-scan-health-refusal-20261026-311.json)。静态 profile 证据见[准备报告](n08-rear-short-hold-slow-descent-profile-20261026-311.md)。运行目录：`artifacts/runs/n08-cancel-highspeed-prescan-20261026-311/`。

## 下一步

只延长该 profile 第 7 阶段 1.2 m 回程时间 60→100 s，其他含 12 s 下降的配置不变。假设较慢的观测回程减少视觉 residual 尖峰；若再次在该阶段 lockout，则停止微调这一路线并从当前证据重新评估可行动路径。任何 N05 或 N08 准入失败都不发目标、不 enable。
