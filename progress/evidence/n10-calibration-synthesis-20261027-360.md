# N10.3 校准证据汇总与状态（#360）

## 当前结论

N10 当前不再因 VINS 质量或源龄策略门拒绝起飞／任务。`tools/project.sh sim` 新会话默认启用 `D435I_DIAGNOSTIC_BYPASS_HEALTH_GATES=1`；特征数、normalized cost、bias、solver 时长、VINS 初始化等待和六路输入 freshness 仍采集并报告，但不用于定位健康策略锁存。`config/components/localization/health.json` 的原始数值未改，normalized cost 1.0 现在仅作为诊断对照值。

旁路不关闭会话／epoch 身份、消息结构、源戳单调性、PX4／桥的时钟与遥测控制条件、地图身份，以及 official_ego 的 inflated-occupied 碰撞处理。#359 实际观测到 `normalized_cost_exceeded` 被旁路，cost 峰值 1.26378 仍继续完成取消、停止和安全降落。这确认主要的定位质量策略门不再拦截当前 N10 诊断动作。

## 到达位置与 yaw 联合评估

新增只读评估器 `tools/debug_truth/evaluate_n10_arrival.py`，用固定一次 SE(3) 对齐、模型 IMU 杆臂和仿真真值，在同一窗口同时计算位置和 yaw。评估覆盖 goal source stamp 至首次 LANDED，而不在 action success 时截断，因此包含目标后的实际保持。它不把真值送入导航或控制。

#357 在 GOAL F 默认 0.30 m、15°条件下，最长联合达标窗口为 243.28 仿真秒／319.06 墙钟秒，窗口内最大位置误差 0.29994 m、最大 yaw 误差 9.1284°，真值最大采样间隔 0.020 s。位置和 yaw 两个条件确实同时满足。GOAL F 未指定 3 秒驻留用哪种时钟；本报告同时保存两个域。该结果超过 3 秒，但仍是单次诊断 run，且健康旁路下的执行不构成最终 N10 资格。

## 速度与停止量测

配置 `max_vel=0.8 m/s/轴`、`max_acc=0.25 m/s²/轴`、`planning_horizon=5 m` 不等同于机体向量速度上限。#357 的 EGO 参考峰值为 0.71138 m/s，PX4 实测峰值为 0.63582 m/s；同一配置的 #354 参考／PX4峰值为 0.67767／0.61035 m/s。#359 选在 PX4 实测 0.50–0.56 m/s 区间取消：触发 0.50024 m/s、EGO 参考 0.53017 m/s；取消确认 0.00082 墙钟秒，新停止轨迹在 0.032 仿真秒出现，4.96 仿真秒后首次进入停止速度带。

#359 的真值水平路径长度为 1.30447 m，PX4 停止带连续保持 1.0 仿真秒，停带期间真值水平最大位移 0.00756 m。低速 #321 在 PX4 0.04014 m/s 触发时测得取消至停止 0.30407 m。两点说明配置速度值、EGO 参考速度与 PX4 实际速度必须分别报告；现有样本尚不足以拟合通用制动模型或确定安全制动预算，#359 也只有一个高速样本。

## 误差、地图、净空与时效现状

- #357 raw VIO 覆盖 667.888 仿真秒和 24.544 m 真值路径：位置误差 RMSE 0.3462 m、p95 0.4971 m、最大 0.5135 m；绝对 yaw 误差 p95 8.6921°、最大 8.7632°；有界时间支持 0.999946，raw 最大间隔 0.068 s。
- #357 EGO 参考对真值的 tracking error p95 0.52058 m、最大 1.09925 m。0.15 m 候选值明显不获数据支持，不能冻结。
- #357 goal 至 landed 的 map source age 峰值 0.164 s、occupancy age 峰值 0.100 s。0.4 s 仍只是旧候选值，现有样本不能单独证明最终年龄预算。
- 离线用本轮冻结 SDF 与 provisional `vehicle_envelope.json` 复算，#357/#359 的采样净空最低值分别为 0.44586 m／1.40410 m；以实际观测到的最大相邻样本机体位移作扣减后分别为 0.42859 m／1.38836 m。这个扣减不是连续动力学上界，机体模型也仍是仿真 provisional 值，因此只能作为正净空的采样证据，不能冻结最终最小间距。
- 重规划时限、源龄／融合龄最终界、地图几何误差预算、raw VIO 误差预算、跟踪阈值和故障检测／退出时间仍未形成可独立复核的数值依据。

## N10 状态与下一步

N10.1、N10.2 已完成。N10.3 仍在进行；当前缺口是把上述单次／少量校准证据转成有物理理由和明确时间域的最终支持范围。高速取消距离只有 #359 一次，后续需用冻结的同一协议补足重复性，再据此讨论停止预算。完成这些判断后再进入 N10.4 唯一 acceptance 配置与统一 evaluator；N10.5–N10.7 尚未完成。

本报告只关闭 N10.3 的此次证据汇总，不把父 N10 标为通过，也不改变 GOAL F 的 0.30 m／15°／3 s合同。

## 复算产物

- #357 联合位置/yaw 评估：`artifacts/runs/n10-20261026-357-upstream-spline-speed080-health-bypass-16m/n10-arrival-evaluation.json`
- #357 长航线：`artifacts/runs/n10-20261026-357-upstream-spline-speed080-health-bypass-16m/n10-calibration-evaluation.json`
- #357 净空：`artifacts/runs/n10-20261026-357-upstream-spline-speed080-health-bypass-16m/n10-clearance-evaluation.json`
- #359 取消制动：`artifacts/runs/n10-20261026-359-high-speed-cancel-stop/n10-cancel-braking-evaluation.json`
- #359 净空：`artifacts/runs/n10-20261026-359-high-speed-cancel-stop/n10-clearance-evaluation.json`
- #321 低速取消对照：`artifacts/runs/n08-cancel-highspeed-prescan-20261026-321/n08-braking-evaluation.json`
- 机器可读摘要：`progress/evidence/n10-calibration-synthesis-20261027-360.json`
