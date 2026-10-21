# P5 PX4、VIO、建图与 EGO 负载诊断

- 用户持续目标为完成 `GOAL.md` P0–P6 与 A–H；本轮继续本地被动 SITL，车辆保持 disarmed，PX4 bridge 保持 DISABLED，不使用 truth 输入或控制输出。
- #115 首次尝试在 EGO 配置读取时因工作目录错误退出；原始日志和脚本保留，未计验收。#116 修正 harness 工作目录，在 ROS domain 232、固定 `d435i-vins:dev` 镜像及 PX4 v1.17.0 下运行45秒诊断组合，含 VINS、定位、mapping、EGO、traj_server、navigation supervisor 和只读探针。
- #116记录RTF 0.362599、observed_offset斜率−0.637701秒/墙秒、一次estimated_offset归零，以及 `/clock` 收包间隔P95 65.168 ms、最大333.120 ms。mapping收到401条深度、248条优化里程计及416组配对样本，地图占据点最多1,189。
- goal前1秒新鲜度门失败，未发送action goal；没有B-spline。PX4仅收到2条VIO，最新时间映射错误为`clock_mapping_residual_high`，未观察到EV position/yaw融合。控制计数为零、GNSS aiding flags全零、无truth输入、disarmed。
- 对比#114的RTF 0.417311及EV融合，#116时间表现更差，但多出的节点和只读探针都改变了负载，不能归因给某个组件。16核主机与无cgroup限额的30个容器统计样本不证明主机整体饱和。
- 下一步保留#116组合，用受控负载消融区分mapping、EGO与探针开销；对齐PX4拒绝事件与 `/clock` 长间隔。现有freshness门不放宽，不调整offset滤波器。P5仍进行中。
