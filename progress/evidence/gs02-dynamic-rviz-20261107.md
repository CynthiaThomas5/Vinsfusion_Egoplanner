# GS02.3 Debian 动态 VINS/RViz 连续性验证（2026-11-07）

## 范围与运行

- 冻结基线：`gs02-20261106-freeze01`；Debian 固定入口 `uav-groundstation experiment-start`；run `hw10-groundstation-20261106T104050Z`，epoch `c0ff21b5d14e42c6922aa98581b0b799`。
- 纯 `perception --visuals`。记录的 `px4_outputs=not_started`；无地图、规划、EV、bridge/control、模式、武装、起飞或固件/参数更改。
- 用户完成短时绕圈并报告“全程没有卡顿”。系统在移动前记录20个位姿静止基线，停止前正常等待返回段并调用 `uav-groundstation experiment-stop`。

## 位姿与定位

- 记录器运行366.713秒，共2152个位姿，最大接收间隔0.526秒。以20条静止基线的位置中位数为参考，轨迹离参考位置超过0.30米的窗口从运行后128.233秒到152.645秒；最大估计偏移3.707米，终点估计偏差0.113米，整段估计路径长9.155米。没有独立真值，这些是VINS轨迹内部统计，不作为绝对精度结论。
- 同期Nano本地日志包含27条定位健康观察，27条均为`TRACKING`。Nano本地pose source age P50/P95/最大为0.337/0.401/0.468秒；左右相机source频率约15Hz，propagated约193Hz，optimized在采样窗口最低约6.44Hz。
- Debian在运动窗口及前后各2秒收到121条状态样本，全部`TRACKING`且valid；状态采样P95/最大间隔0.296/0.336秒。

## Reader与窗口绘制

`visual-receive-events.jsonl`按Debian接收monotonic时间计算间隔；Nano→Debian时延使用同一窗口最近的时钟偏移估计（不确定度最大1.024ms）。

| 通道 | 运动窗口事件数 | 接收间隔 P95 / 最大 | Nano发送→Debian接收 P95 / 最大 |
|---|---:|---:|---:|
| body | 493 | 85.7 / 410.3 ms | 50.8 / 355.5 ms |
| camera | 186 | 211.5 / 526.1 ms | 40.0 / 370.9 ms |
| history | 48 | 692.9 / 805.7 ms | 27.8 / 221.7 ms |
| image | 123 | 300.1 / 573.7 ms | 126.4 / 371.6 ms |
| points | 186 | 211.7 / 522.8 ms | 42.9 / 367.5 ms |

- 直接从RViz X11客户窗口以5Hz采样174.8秒，2972×1580，共874帧；全窗口874个灰度SHA帧均不同，相邻完全相同帧0。捕获起点距静止基线约118.435秒，完整覆盖上述运动窗，且在运动后继续采集约140秒。
- 位姿运动时间对应视频约9.799–34.211秒；按前后各2秒扩展后分析143个帧及143对相邻帧。左侧双目特征预览ROI和右侧3D视图ROI在每对中均有超过3灰度级的变化；中位变化像素分别为64,161和35,645。中途与运动后截图显示双目跟踪、稀疏点、机体和轨迹持续呈现。
- 画面采样测的是X11窗口位图，不是每次GPU present或显示器扫描输出；用户现场观察也报告无卡顿。
- 状态文本的`pose_source_age_s`在Debian侧P95/最大为1.507/1.555秒；相同`pose_stamp_ns`在Nano本地日志中的source age P95/最大为0.401/0.468秒。按日志时间戳配对估算，Nano `localization.log`到Debian状态样本路径的额外延迟P50/P95/最大约0.630/1.134/1.234秒。这是1Hz定位日志/SSH状态路径，不是上述图像、点云、机体可视relay的延迟；视觉通道另按逐条发送/接收事件统计。

## 资源、停止与原始数据

- 运动窗口内host load最高2.29，可用内存最低8.15GiB，viewer RSS最高183.2MiB，容器内存最高419.0MiB；cgroup CPU throttling增量0、OOM增量0。`wlp6s0` RX/TX错误与drop增量均为0。
- `experiment-stop`正常完成。复核时Debian无统一会话且`d435i-gs-view`容器数为0；Nano统一会话和独立传感器会话均为空；`rmem_max=212992`；`microxrce-agent.service`仍active并走CH340/TELEM1。
- 原始运行目录：[`artifacts/runs/hw10-groundstation-20261106T104050Z/`](../../artifacts/runs/hw10-groundstation-20261106T104050Z/)。像素统计见[`rviz-dynamic-paint-metrics.json`](../../artifacts/runs/hw10-groundstation-20261106T104050Z/groundstation/rviz-dynamic-paint-metrics.json)，完整窗口采样视频SHA256为`f2d16bfb5edfb59cca790019c8da2388eeb54a2e4dc063b90a0e603211942ac7`；运动中截图为[`rviz-dynamic-mid-motion.jpg`](../../artifacts/runs/hw10-groundstation-20261106T104050Z/groundstation/rviz-dynamic-mid-motion.jpg)，运动后截图为[`rviz-dynamic-post-motion.jpg`](../../artifacts/runs/hw10-groundstation-20261106T104050Z/groundstation/rviz-dynamic-post-motion.jpg)。`RUN-SHA256SUMS`覆盖完整Debian和Nano原始目录。

## 判定与限制

本次Debian冻结版本的短动态绕圈、五路可视数据接收及实际RViz窗口采样均未出现长停顿，满足本轮动态演示连续性出口。之前另一次run记录的13.2–20.6秒reader滞后在本次没有复现；其历史触发条件仍未定位，不能声称已被修复。当前处置为：迁移后的固定版本可复现该VINS视图；历史异常作为未定位、非复现观察保留，若再次发生再按同一时钟/reader/资源/窗口流程采集，不据此改固件、门限或PX4参数。

本报告不授予HW08/HW10控制或飞行资格；真实机体安装后的验证仍按主线要求单独完成。
