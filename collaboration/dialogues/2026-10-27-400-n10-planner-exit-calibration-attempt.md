# 2026-10-27 N10.3/#400 规划器退出校准尝试

- 用户授权继续完成 N10，并此前明确允许一次 emergency disarm；该授权已在 #391 使用。本次不再使用 emergency disarm。
- 用户询问是否有问题卡住。答复：当前没有本项目 SITL 运行，但 N10 仍有故障终态、净空区间、误差预算等证据缺口。随后继续 #400。
- #400 使用独立 run-local 协议和工具，freeze 的 runtime contract 为 `4bd013db9195cb7b424a00259872d5dd678450b200fb577df4cf423213b0973b`。注入器等待唯一活动 goal+epoch、有效 bridge 状态、action status 和唯一 planner PID/start ticks，计划在目标起始后 5 仿真秒只发一次 SIGTERM。
- 保护条件单测 5 项通过，prelaunch 身份/源码/参数一致。SITL 起飞及 action 提交成功，但注入器未发信号：action status 被标为 stale/missing，最终同时看到 bridge 不再 ACTIVE，因此拒绝。ROS graph 显示 action status publisher durability 为 transient-local，而注入器原订阅为 volatile；怀疑这是主要观察器配置原因，作为推断记录，待修 QoS 后验证。
- 本次独立出现 PX4 `px4_local_position_invalid`：bridge 在 sim 119.316 s 进入 LANDING，124.536 s LANDED。navigation action 在 bridge landed/disarmed 后仍保持 executing；对精确 goal_id `b893b44e86244a739fcedad6d3a7b74f` 在 epoch `43b696c43df04fb795ac4dd4e136f5ce` 上执行了一次 action cancel，service 接受。没有紧急 disarm。
- 15 秒 postflight probe 的 landed/disarmed/control-disabled、PX4 disarmed/land_detected 和 zero-control 通过；仍观测 1,099 条匹配 goal/epoch 的 READY PositionCommand，terminal evaluator 的 no-old field 为 false，fault terminal insufficient。现有样本不能区分 stale movement 和取消 stop-hold，未作碰撞推断。
- 传感器 bag 离线可读取，但 capture 因外部 shutdown、未覆盖 safe terminal、run identity 缺 map_id 而 insufficient；资源/真值/接触/净空最终评估缺失。物理安全读回通过后，仅按项目正常流程停止容器，exit 0。
- #400 不算 process-exit 校准通过，不加入 N10 完成子项。下一子项 #401：在不增加健康/起飞门的前提下，bridge 进入既有 LANDING 安全路径时向 navigation 发布匹配 goal_id+epoch 的 fault abort；修 action status QoS 与 observer 收尾；测试、构建后重新校准。N10 保持 `in_progress`，N15/N16 仍在冻结后。
- 证据：[报告](../../progress/evidence/n10-planner-exit-calibration-attempt-20261027-400.md)、[JSON](../../progress/evidence/n10-planner-exit-calibration-attempt-20261027-400.json)。
