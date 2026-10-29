# #357 N10.3 独立冷启动复测协议

## 假设与判据

#355 在同一路线完成到达和600仿真秒保持，但观察不完整；#356 的完整观察 run 在前进约2.60m后记录 EGO 候选样条反复撞上官方 inflated occupancy 并 planning_failed。本次以独立 Gazebo/PX4/VINS/map 冷启动保持所有任务和planner设置不变，判断该规划失败是否重复出现。

若达到目标并完成3秒驻留、600仿真秒保持且五类终态观察均完整，保留为诊断校准样本。若再次在目标前发生相同 planner_full_curve_planning_failed，则停止重复航线，转只读膨胀占据碰撞诊断；不改碰撞策略或健康阈值。

## 冻结设置

- EGO：max_vel=0.8 m/s/轴，max_acc=0.25 m/s²/轴，horizon=5 m。
- 航线：同一16m/3D/yaw单目标，3秒驻留，600仿真秒ACTIVE保持。
- 定位质量/源龄策略旁路：仅本次诊断运行开启；health.json 和 normalized-cost=1.0不变。
- 观察器：等待终态 flight.json，最大墙钟1500秒；检查接触、raw VIO、对齐和PX4末态。
- 新增的后处理修复只将分析器从冻结目录复制到run目录并校验SHA，不影响飞行参数或二进制。

## 冻结身份

- runtime contract：c8a1ee4f5d91d3db7454a9d4608e6ad7e8e09fced7c4c4e2782547760c702e23（659 文件）
- driver SHA-256：d1484926cf0b33b212db44fa3d64360569a2e8d8b06e265305235dbec3f8785d
- analyzer SHA-256：f94812ecdc16006513f987952398f8240fb1beab36d452cbee54628864017ba8
- 结果目录：artifacts/runs/n10-20261026-357-upstream-spline-speed080-health-bypass-16m/

机器可读协议：[JSON](n10-upstream-spline-speed080-health-bypass-open-speed-16m-protocol-20261026-357.json)。
