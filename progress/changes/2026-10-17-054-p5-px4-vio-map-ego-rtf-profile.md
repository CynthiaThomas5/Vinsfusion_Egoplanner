# P5 VIO、建图与 EGO 负载下的 RTF 诊断

对话摘要：[2026-10-17-054](../../collaboration/dialogues/2026-10-17-054-p5-px4-vio-map-ego-rtf-profile.md)。

## 结果

- #115 首次启动在 EGO 配置读取时因 shell 仍位于 PX4 build 目录而退出，未启动 planner/action，也未开始 profile 探针。保留启动错误、日志和原始脚本；不计验收。
- #116 修正工作目录后，在 Jazzy/Gazebo Harmonic/PX4 v1.17.0、ROS domain 232 中运行45秒被动 SITL。组合含单 D435i、VINS、定位、深度健康门、建图适配器、EGO `plan_env`/FSM、traj_server、navigation supervisor、PX4 lockstep、Agent 和只读探针。车辆静止、disarmed，PX4 bridge 保持 DISABLED；没有控制、轨迹飞行或 truth 输入。源码、阈值和相机规格未改。
- mapping probe 记录401条深度输入、248条优化里程计、416组同 stamp 深度/pose输出，最多1,189个占据点；地图 frame 属于当轮 epoch。地图几何和规划任务未验收。
- navigation probe 观察到 TRACKING 与非空地图，但1秒稳定输入门未通过：目标前 odometry 新鲜度检查失败1,179次，pose/depth配对新鲜度失败352次。没有发送 action goal，也没有 B-spline；EGO 处于 WAIT_TARGET。这说明当前负载下导航入口按既有 freshness 条件 fail closed。
- 3,885个 `/clock` 样本跨越43.056秒墙钟与15.612秒仿真，RTF为0.362599；observed_offset OLS斜率为−0.637701秒/墙秒，约11.831秒有一次 estimated_offset 归零。clock收包间隔P95 65.168 ms、最大333.120 ms，470/3,884个间隔超过20 ms。
- PX4 只收到2条外部视觉里程计，bridge detail记录330次 `external_odometry_stale`、5次 `px4_telemetry_stale`，最新时间映射错误为 `clock_mapping_residual_high`；未观察到EV position/yaw融合。GNSS aiding flags全零，ROS truth topic与bridge truth订阅均未发现，控制样本为零，车辆保持disarmed，readiness覆盖率为0。
- 主机和容器均有16个逻辑CPU，容器没有CPU/内存上限。Docker stats 30个样本中CPU中位606.39%、峰值812.06%，内存中位1,549 MiB、峰值1,741 MiB。进程的 `ps %CPU` 是启动以来平均值；Gazebo进程（`ruby`）样本中位179%、RSS中位831 MiB。没有主机整体CPU饱和证据，也不能把RTF退化归因到某个单独进程。
- 对照 #114 的 VINS+定位 profile（RTF 0.417311、280条VIO并观察到EV融合），#116增加建图/EGO/navigation进程后测得更低RTF、offset漂移更大，且PX4拒绝绝大多数VIO。新增节点和探针也增加负载；这组对照不能单独证明建图或EGO是根因。

#115、#116的脚本、日志、ULog、探针输出、资源曲线及源文件哈希见[轻量证据](../evidence/p5-px4-vio-map-ego-rtf-profile-20261017-116.json)和[run artifacts](../../artifacts/runs/p5-px4-vio-map-ego-rtf-profile-20261017-116/)。

## 验证与下一步

- `bash -n` 验证#116 harness、host launcher、resource sampler；`python3 -m py_compile` 验证离线分析与 qualification 脚本。#116的 `/clock`、offset、CPU和内存统计从已保存样本离线复算。
- `python3 tools/project_status.py`、`git diff --check` 与证据哈希复核在更新状态记录后运行。
- 下一步用相同PX4镜像、world、domain隔离策略和探针做负载消融，区分 VIO/localization、mapping、EGO与观察器负载；同时追踪 `clock_mapping_residual_high` 与 `/clock` 长间隔的对应关系。goal 稳定门未通过前不发送任务，不放宽 freshness 阈值、不改PX4 offset滤波器。P5、P4、P6和GOAL A–H仍未完成。
