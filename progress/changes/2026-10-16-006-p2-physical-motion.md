# 动态台架缺失平移加速度的根因与修复

对应[对话摘要](../../collaboration/dialogues/2026-10-16-006-p2-physical-motion.md)。

## 发现与对照

- 在 p2-ablation-20261016 中，将相同双目输入同时送入完整 VINS 和仅双目诊断节点；分别生成独立 epoch，参数、图像和源码可追溯。仅双目仅为诊断，未成为最终组合。
- 完整 VINS 单 SE(3) 位置 RMSE 0.921 m；仅双目 0.0815 m。已录 MCAP 和实际订阅图，不含真值位姿订阅。完整最终链尚未实现，不计作 GOAL B3 通过。
- tools/check_render_geometry.py 独立投影已知平面标记，记录图像角点相对模型／真值投影的误差中位数约0.724 px，未发现足以解释米级漂移的图像几何误差。
- 直接检查原始 IMU：x/y 加速度范围仅约1e-17 m/s²，z 始终9.80665；模型却在加减速。先前微分 RMSE0.037被误认为小幅采样误差，实际上漏掉了整段平移加速度。此处更正先前解释。
- 因此旧动态数据并非运动一致的双目＋相机 IMU，不能用于 VINS 精度验收。原始记录、旧实现快照与测量结果保留。

## 修改

- GOAL.md 仅同步开头状态为实施中；最终目标、范围、A–H 条款与完成条件保持原文。

- tools/prepare_motion_world.py：移除 VelocityControl，改为 Gazebo ApplyLinkWrench；校准刚体仍由同一 SDF 生成，模型质量／惯量不另手抄。
- tools/run_sensor_motion.py：只按仿真时钟发送世界系物理力／力矩，不设置位姿或速度，不使用真值反馈。持续力按增量叠加，结束时清理本模型持续力；不影响其他模型。
- config/components/simulation/sensor_motion.json：固定台架阶段、三轴加速度和 yaw 角加速度协议。将执行时的常量外移后，3001个时间点的命令与原执行版本完全一致；保存 motion-driver-executed.py 原执行文件。
- tools/test_motion_tools.py：覆盖力驱动世界、单刚体、命令范围、理想阶段积分回到静止，防止退回速度覆盖方式。
- tools/probe_vins.py：记录真实节点订阅／发布图。

ApplyLinkWrench 的持续输入会累加，故只发布相邻阶段的差量；实现依据见 [Gazebo 上游源码](https://github.com/gazebosim/gz-sim/blob/gz-sim8/src/systems/apply_link_wrench/ApplyLinkWrench.cc)。本项目调用已安装插件，没有复制／修改上游源码。

## 实际复测

- p2-force-motion-20261016：重新冷启动，VINS 源码、二进制及非几何参数与此前一致，没有调噪声权重或改门控。
- 三轴真值运动跨度约0.277／0.320／0.138 m，yaw 约26.43°；相机 IMU 已出现物理平移加速度。
- 单次 SE(3)、固定尺度1：373个位姿，24.55 s 重叠；位置 RMSE **0.02533 m**、最大误差 **0.05060 m**；姿态 RMSE1.517°。
- IMU 比力相对真值导数 RMSE0.00191 m/s²、yaw角速度 RMSE0.000043 rad/s；角点投影误差中位数约0.721 px。
- MCAP、truth／IMU、原始优化／传播输出、求解遥测、节点图、配置、日志与哈希见 [证据](../evidence/p2-physical-motion.json)。所有失败／诊断 run 保留。
- test_motion_tools.py 3 项、test_vins_config.py 2 项通过；源码编译检查、结构检查、git diff --check 通过。本轮未改 ROS 包 C++，复用了已核验二进制。

## 局限与下一步

这是一次理想台架的预校准，正式阈值未冻结，P2 不标 passed。健康门控、输入断流／重启／时间倒退、传播 twist frame、重复独立校准、飞机传感器安装和最终闭环仍待完成。旧台架异常不是 VINS failureDetection 无条件关闭的理由，该问题仍须解决。不将仿真测量外推真实 D435i。
