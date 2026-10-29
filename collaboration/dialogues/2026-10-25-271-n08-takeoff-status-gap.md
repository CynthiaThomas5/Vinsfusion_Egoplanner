#271 对话摘要

- 用户的返航要求继续作为硬约束：原地转向约 180°并确认航向，然后由 EGO 沿机头前向重新规划；不倒飞。#271 未执行返航动作。
- 正确 N08 低速 profile、N05 释放后和 mission current-area 准入、40.00149 s preflight、起飞前 capsule/home-pad 证书通过。扫描仍有未归因的泛化定位警告。
- enable 后 PX4 解锁并检测起飞；bridge 未达到 ACTIVE。记录到 `/localization/status` 0.344954 s 回执空窗，超过现有 0.2 s freshness 门，前后状态均 valid TRACKING。runner fail-closed 并降落。EGO goal 未发，vertical settle 未运行，没有新制动数据。
- 负载假设：N08 未用的 `/grid_map/occupancy` PointCloud2 observer 仍在起飞阶段订阅，可能延迟状态回调。#272 已把销毁 observer 移至 raw map/home-pad 证书通过后、enable 前；保持 freshness 门与其他验收条件不变，待 fresh SITL 验证。
- 证据：[`#271报告`](../../progress/evidence/n08-preactive-localization-gap-20261025-271.md)、[`改动记录`](../../progress/changes/2026-10-25-271-n08-takeoff-status-gap.md)。
