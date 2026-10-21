# 任务对话摘要

- 日期与任务 ID：2026-10-20，继续项目 Goal；P5 anisotropy filter 对照 #210–#213。
- 用户目标与明确约束：继续推进单 D435i 仿真导航；不使用在线真值或完整世界地图；保留定位质量、freshness 与 PX4 安全门；诊断结果不能写成 P5 或 GOAL 验收。
- 已确认的决定：以 #210 无过滤的 0.30 m 横移／+30° yaw 作为同 domain 对照，比较 run-local `0008` 的 0.01、0.001 与 0.0025 阈值。补丁不进入 canonical VINS；不修改现有安全门。
- 已确认的结果：四轮均通过稳定前置门并派发目标，均未完成目标。#210 未过滤时 cost=1.2530；#212 的 0.001 保留 40 个 >1.5 px 残差块、cost=1.0353；#213 的 0.0025 保留 21 个高残差块（该组 tensor ratio 0.00311–0.00640）、cost=1.0425。#211 的 0.01 样本没有 >1.5 px 残差块，但 action 先因 `accel_bias_norm_exceeded` 中止；当时 normalized_cost=0.4442，之后样本达到1.0027。独立 run 间结果只支持观测关联，不证明因果。
- PX4 结果：四份 ULog 均无 dropout，EV aiding 有记录，GNSS aiding flags 为零；均记录触地和最终解除武装，触地后有短暂 DESCEND/failsafe。#213 flight report 未捕获最终 disarm，但 ULog transitions 记录了该状态。
- 实施范围：只读分析并归档四轮 SITL、残差图像关联、ULog 时间线；更新证据索引、CURRENT、里程碑证据引用和 checklist evidence；无 canonical 源码或阈值改动。
- 待确认：偏置门触发与低各向异性残差的关系、阈值跨 run 的有效性及导航精度影响均未确认。停止单次阈值 sweep；下一步读取现有 estimator/health/轨迹时间线，定位 bias 与残差事件关系，再决定其他受控干预。
- 对应改动记录：progress/changes/2026-10-20-009-p5-anisotropy-filter-horizontal-paired-runs.md
