# P5 VIO–PX4–EGO 受控飞行诊断（#153–#159）

## 范围与约束

继续推进 `GOAL.md` 的 P4/P5 单 D435i 仿真链路。P0–P3 阶段表状态保持不变；语义、信念和探索仍只预留接口。无真值 VIO 组合不订阅 debug_truth 或完整世界地图；PX4 Offboard 控制只能由 `uav_px4_bridge` 发布。任何短 SITL 冒烟都不能替代回放、SITL 长时、实机或正式阶段验收。

## 本轮决定

- 保留 localization freshness 的整数纳秒边界比较，避免 300 ms 浮点舍入误报。
- 每条 PX4 遥测使用其接收时捕获的 `TimesyncStatus.estimated_offset` 计算源龄，避免后续 offset reset 追溯改写缓存样本年龄。
- 只在 `vio_closed_loop` profile 中将 PX4 源时间戳未来容差设为 50 ms；依据 #157 观察到的 41.048 ms 最大提前量。source stale、receipt、共享/debug_truth 和 localization 质量阈值保持原值。
- #158/#159 都到达 ACTIVE 并发出目标，但因归一化残差质量门超限中止并安全落地；不据此放宽 `max_normalized_cost=1.0`。

## 证据与未决项

P5 轻量报告 `progress/evidence/p5-vio-ego-closed-loop-20261019-153-159.json` 记录 #153–#159 结果、hash、健康指标和验证范围。#159 的只读观测表明 raw depth 与 depth-health 继续到达，健康锁定后 optimized odometry 与 EGO 深度/位姿转发停止。历史健康建图与视觉退化回放成本分布不覆盖飞行运动，1.067/1.128 两个值对应的真实轨迹误差尚无对照。下一步记录完整 `LocalizationStatus` 指标时间序列并关联图像/运动与 VIO 误差；保持质量门关闭直到阈值有精度证据。P5 仍进行中，目标动作未成功，未完成 GOAL A–H。
