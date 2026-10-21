# P5 VIO + localization RTF 与资源剖析

对话摘要：[2026-10-17-053](../../collaboration/dialogues/2026-10-17-053-p5-px4-vio-rtf-profile.md)。

## 结果

- #114 在 Jazzy/Gazebo Harmonic/PX4 v1.17.0 中运行45秒被动 SITL，保留 D435i、PX4 lockstep、XRCE Agent、VINS、定位适配器及 DISABLED bridge。ROS domain 230，未启动 mapper/EGO，不发布控制，也未解锁。PX4 与桥接源码、参数阈值及控制行为未改。
- 4,678个 `/clock` 样本跨越44.830秒墙钟、18.708秒仿真，RTF为0.417311；TimesyncStatus 41条，`observed_offset` OLS 斜率为−0.583264秒/墙秒。约14.7942秒有一次 `estimated_offset` 归零，下一条样本约0.391 ms后重建。两种速率延续 #112 的慢 lockstep / Agent wall-clock 关系；#113在无VINS/localization时保持RTF约1且无reset。
- `/clock` 收包间隔中位数4.059 ms、P95 51.515 ms、最大58.603 ms；566/4,677个间隔超过20 ms。无重复时钟样本或回退。间隔长尾说明时钟推进不均，但不足以确认哪个执行路径造成停顿。
- 主机及容器均报告16个逻辑CPU，cgroup无CPU或内存上限。Docker stats 26个采样中位498%、峰值734.28%；采样覆盖启动、45秒探测及退出。`docker top` 的 `ps %CPU` 是进程启动以来的平均值：Gazebo进程（`ruby`）中位154%、最高240%、RSS约819.5 MiB；VINS中位54.25%；定位适配器中位29.4%；bridge中位24.5%。未见主机整体CPU饱和；这些采样不能定因。
- 定位进入 TRACKING，279条 optimized localization odometry、280条 PX4 外部视觉里程计输入，PX4 EKF2 观察到 EV position/yaw fusion；GNSS aiding flags全零，未发现ROS真值topic或bridge真值订阅。车辆保持 disarmed，控制/轨迹设定点/命令采样为零。
- readiness末端10秒覆盖率为0，bridge保持 DISABLED；probe记录43/343条 `px4_telemetry_stale` 和284/343条 `px4_preflight_failed`。Harness结果为FAIL，准确含义是 readiness 条件未满足；该run没有启用bridge，不能据此称为融合失败，也不能作为P5通过。此处保留 fail closed，没有放宽门槛。
- #114只包含 VIO 与定位负载；尚未覆盖建图、EGO规划，也没有轨迹或导航测试。完整导航栈性能仍待 profile。

原始数据、离线分析程序、PX4 ULog、脚本和源文件哈希见[轻量证据](../evidence/p5-px4-vio-rtf-profile-20261017-114.json)及[run artifacts](../../artifacts/runs/p5-px4-vio-rtf-profile-20261017-114/)。

## 验证与下一步

- `bash -n` 对运行脚本与资源采样脚本通过；`python3 -m py_compile` 离线分析脚本通过。离线分析从保存的 `/clock`、TimesyncStatus、Docker stats 和 `docker top` 样本复算指标。
- `python3 tools/project_status.py`、`git diff --check` 和证据哈希核对在写入状态记录后执行。
- 下一步在相同相机规格与健康门下加上 mapper/EGO 负载重复 RTF profile，并针对长 `/clock` 间隔检查 Gazebo 与 ROS 回调调度；不先改 PX4 offset 逻辑或放宽 freshness 门。P5、P4、P6 与 GOAL A–H 仍未完成。
