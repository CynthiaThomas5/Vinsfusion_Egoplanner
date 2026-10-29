# N10.2 证据覆盖与风险处置（#335）

**结果：N10.2 审查完成；N10 仍在进行。** 本项复核 N01–N09 的原始证据、当前 official_ego 策略和 GOAL F，将可复用证据与仍缺量测分开，给每个未解点指定了处理动作。未运行新实验或飞行；历史通过结果保留原范围，不作扩大解释。

## 证据覆盖决定

| 目标 | 可复用内容 | 当前边界与处理 |
| --- | --- | --- |
| N01 原始 VIO | 3 个 fresh epoch；最长 8.395 m、344.784 仿真秒；10 s 平移 RPE RMSE 最大 0.01374 m，位置 ATE 最大 0.06724 m | 是低速未武装支架支持运动，且无 roll 激励。不能外推到 16 m 飞行或 600 s。N10.3 做长航点和延长观测。 |
| N02 健康/时序 | 正常支持运动 #085/#086 最高 normalized cost 0.640/0.973；N09 repeat03 的 1.10066 被原门限捕获并安全落地 | #02、#04/#05 事件原因未知，不叫误报／修复；门限不动。健康故障按失败并安全退出处理，不能算成功任务。 |
| N03 深度融合 | 3 个 150 s 独立 idle epoch；地图查询年龄最大 0.168 s，融合源间隔最大 0.10 s；断流后关闭 gate、reset、重建新 map identity | 不是飞行中的定位/到达误差证据。复用现有 0.4 仿真秒 source-age gate，N10.6 在重建后确认实际运行参数与持续新鲜度。 |
| N04 地图 | 两布局、三快照；最大表面 residual 0.09535 m，栅格分辨率 0.10 m；fusion source-to-complete 最大 0.149 s | 原出口没有定量误差阈值；corridor 一张图有约一格墙面移动和 raw 误分类冲突。N10.3 验证以一格为候选上限；实际机体净空用只读真值/接触评估。 |
| N05/N06 策略 | N09 当前策略下无支架垂直起飞 3 次；#331 对 unknown 保留、inflated occupied 拒绝、越界和旧 epoch 的 live probe 通过 | 旧 N05 raw-known-free 支架门属于历史规则；N06 曲线是 planner-only 且没有在当前 official 策略下执行。N10.6 查在线语义；N12–N14 做正式障碍飞行。 |
| N07 PX4 时间 | 3 个累计成功冷启动与地面 PX4 时钟读回通过；用户要求已通过项不复测 | N10 未计划改 HRT 时间映射。保留 N07 证据，N10.6 观察重建后的 PX4 时间/telemetry。 |
| N08 停车 | 同一低速配置三次终点停车：逐轴 0.1 m/s、0.25 m/s²；实际峰值向量速度 0.07550–0.08282 m/s；参考制动到停 0.2811–0.2957 m；最大 tracking 0.0801–0.0867 m | 单程低速、短前向场景；cancel 的 0.3041 m 只对应已测速度窗，0.5 m 是有限样本候选范围。不能推广到 0.5 m/s 默认 planner、返航或未知障碍。沿路径停车距离不加到径向包络。 |
| N09 3D/yaw | 3 个独立成功：约 +0.4 m、+0.1 m 高度、+0.2 rad yaw；地图 source age 最大 0.156 s；repeat03 失败安全落地 | 成功 run 的 profile dwell 为 1 s，独立 evaluator 连续窗约 1.03–1.10 墙钟秒；未证明 GOAL F 的连续 3 仿真秒。也没有 16 m 距离或障碍绕行。保留旧 3/3，不复测同一旧合同。 |

## 风险决策和冻结前动作

- GOAL F 到达条件保持 **位置误差 ≤0.30 m、yaw ≤15°、连续至少 3.0 仿真秒**。旧任务 native dwell 是 1 s；arrival evaluator 当前按 wall time 计算连续时间。N10.4 统一 native dwell 和独立真值判定的 sim-time 参考。
- 默认 16 m mission 目前加载 0.5 m/s 逐轴上限、0.8 m/s²；重复低速证据来自 0.1 m/s、0.25 m/s²。N10 候选固定用低速 profile，并单独测量实际向量速度，最大 0.12 m/s；更快需另行校准。
- 目标超时按仿真时间计算，flight client 却只等待 `timeout_s + 4` 墙钟秒；RTF 小于 1 时可能提前取消。`--flight-timeout-s 75` 只用于起飞后等待 ACTIVE，不是航点超时。N10.3 获取 RTF，N10.4 实现含余量的墙钟 watchdog。
- map source/occupancy age 暂按 ≤0.4 仿真秒；定位源龄和 receipt-age 使用 `health.json` 及 `task_supervisor.json` 现有分时域门限，不放宽。重规划期限还没有当前策略下的端到端证据，需从实际地图更新到替换轨迹记录确定，不能用 0.4 s map timeout 或 #151 查询耗时代替。
- 地图几何候选门限 ≤0.10 m 来自 0.1 m voxel 和 N04 最大 0.09535 m；tracking 候选 ≤0.15 m 采用已有 N08 runtime gate；物理障碍净空候选 ≥0.10 m 用一格作为可读最小间隔，机体参考半径 0.48194 m 和 provisional spatial margin 0.24868 m 仍单独列账。N10.3 核对定义，避免重复相加；候选值在 N10.7 冻结前都不是最终门限。
- 保留 `minimum_occupancy_points` 未被代码消费的发现；N10.4 从活动 goal profile 清理旧字段。运行身份清单需补全 vendor patch、安装 share/launch/config、评估器和 PX4 source。锁定镜像归档缺失的问题在 N10.7 解决。

N02/#332 根因、N04 有限采样 anomaly 和 official_ego 的 optimistic unknown 语义都保留为明确边界；它们不会被写成已修复。若 N10.3/N10.6 显示所需运动范围内净空、视觉误差或 RTF 不足，N10 继续未完成，先修复并重做受影响证据。

完整结构化矩阵见 [#335 JSON](n10-evidence-coverage-20261026-335.json)。下一子项为 N10.3：补齐长距离/长时定位、速度/停车、地图误差与当前策略重规划的独立依据。
