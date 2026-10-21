# P5 PX4/VIO负载消融与 freshness 失锁诊断

对话摘要：[2026-10-17-055](../../collaboration/dialogues/2026-10-17-055-p5-load-ablation-freshness.md)。

## 结果

- #117 因ROS domain设为234（超过Fast DDS上限232）在PX4 DDS实体创建前退出。失败日志、脚本和资源采样均保留，不计性能结果。
- #118/#119 用固定镜像、D435i world、PX4 build、VINS/定位桥与共同只读探针做45秒左右的无mapping/EGO基线。RTF为0.4200/0.4189，observed_offset斜率为−0.5798/−0.5816秒/墙秒；与#114一致。但#118发生0.671秒VINS telemetry/odometry收包间隙并锁定`telemetry_stale`，#119发生clock/传感器同步receipt gap并锁定`propagated_stale`。两轮都没有EV融合，故仅保留时基/故障路径诊断。
- #120运行深度健康门、mapping adapter与探针，RTF0.3636、offset斜率−0.6363。运行脚本未启动EGO plan_env；adapter日志显示map reset barrier一直关闭，地图样本为0。该轮不是活动建图负载，不能用来归因mapping计算。
- #121启动深度门、mapping adapter、EGO plan_env/FSM与traj_server，无navigation supervisor/trace。观察到epoch清图及WAIT_TARGET；随后出现约0.721秒`/clock`和IMU收包空档，定位以`telemetry_stale`锁定，mapping gate关闭，没有占据图输出或PX4 VIO。RTF0.3713、offset斜率−0.6342。EGO重置服务还记录一次timeout warning。
- 全部成功启动的run保持disarmed、bridge DISABLED、控制样本为零、无ROS真值输入。没有发任务目标，也没有调整参数、阈值或PX4时钟滤波。相较#114，加载轮次RTF较低并伴随更大offset漂移；#118/#119的互补关系符合`RTF + abs(offset slope) ≈ 1`。探针和节点启动负载、多次freshness锁定、#120缺少plan_env，使组件级归因仍不成立。

轻量报告、源哈希、运行脚本、ULog与探针输出见[证据报告](../evidence/p5-px4-load-ablation-20261017-117-121.json)。

## 验证与下一步

- 运行前对run-private harness和sampler执行`bash -n`，离线analyzer执行`python3 -m py_compile`；运行后离线复算时钟与资源摘要，报告记录每个运行产物和项目源码SHA-256。
- `python3 tools/project_status.py`与diff检查在状态记录更新后复跑；结构通过不表示P5通过。
- 下一步用启动分段和统一的事件时间线追踪Gazebo `/clock`间隙、VINS telemetry/odometry延迟、定位锁定与mapping gate；不放宽freshness阈值。随后重跑无goal的活动建图+PX4 VIO，只有稳定门满足时再执行导航规划/跟踪验收。P5仍进行中，P4/P6及GOAL A–H未完成。
