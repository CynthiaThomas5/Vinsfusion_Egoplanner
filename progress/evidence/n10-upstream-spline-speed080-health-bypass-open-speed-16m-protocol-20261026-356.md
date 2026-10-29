# #356 N10.3 完整观测诊断复测协议

## 目的

#355 的飞行动作、独立目标驻留、600 秒 ACTIVE 保持和 PX4/桥安全终态读回已通过；但只读观测器在固定 380 墙钟秒停止，早于任务末段，因此接触落地观测和完整 raw-VIO/对齐分析缺失。#356 只修复观测生命周期，不改变飞行参数或任务路线。

## 冻结变量

- 唯一变化：观测器在 flight.json 终态文件出现后退出，1500 秒墙钟超时作为上界，并把终态文件是否已观察到写入结果。运行驱动拒绝把缺少终态观测标记的记录认作完整证据。
- 保持：EGO max_vel=0.8、max_acc=0.25、horizon 5 m；16 m/3D/yaw 单目标、3 秒到达驻留、600 仿真秒 ACTIVE 保持；official_ego 碰撞语义；同一单次定位质量/源龄策略旁路。
- health.json 与 normalized-cost=1.0 未改。旁路只适用于本次诊断，不取得正式健康资格；结构、身份、时间完整性、地图/碰撞、PX4 与 bridge 控制状态检查仍有效。

## 验收观察

记录 raw VIO 全姿态、真值离线误差、planner/bridge 阶段、Gazebo 接触、地图/源龄时序、目标驻留和 PX4 末态。接触评估、VIO评估、校准分析分别报告；任一观测超时或落地接触证据不完整均不记完整通过。

## 冻结输入

- 运行合同：c8a1ee4f5d91d3db7454a9d4608e6ad7e8e09fced7c4c4e2782547760c702e23（659 个文件）
- 运行驱动 SHA-256：487b2c92a638bd0d32d5c290943c3b2456c9c94a70a2dbbcb58f1c5b4448e28d
- 分析器 SHA-256：f94812ecdc16006513f987952398f8240fb1beab36d452cbee54628864017ba8
- Planner：config/components/mapping/n10_horizon5_speed080_calibration.json
- 结果目录：artifacts/runs/n10-20261026-356-upstream-spline-speed080-health-bypass-16m/

完整机器可读协议见 [JSON](n10-upstream-spline-speed080-health-bypass-open-speed-16m-protocol-20261026-356.json)。
