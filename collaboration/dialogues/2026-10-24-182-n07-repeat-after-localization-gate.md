# N07 #182 对话摘要：定位门失败后的新冷启动

## 用户约束

- 继续用户已授权的N07 Goal完成模式，直到N07出口通过。
- 地下不是可飞空间；保持现有ground-boundary规则和N05门限。
- 任何定位失鲜或准入失败都禁止解锁/起飞，先安全释放并确认末态。

## 执行决定

#181的attached N05首次只读检查接受，但两秒settle后的重复gate因`localization_not_tracking`失败；支架安全移除，容器正常停止，N07连续计数为0/3。#182使用全新container和epoch，按真实marker字段`vehicle_arming_state`核实DISARMED，启用shell fail-fast，只做一次明确2秒settle后的attached gate，不在同一epoch重复查询。tracking与全部N05 gates通过后才飞。详情见[#181失败报告](../../progress/evidence/n07-preflight-localization-failure-20261024-181.md)和[执行卡](../../progress/changes/2026-10-24-182-n07-repeat-after-localization-gate.md)。

## 结果与下一项

#182通过，成为重置序列1/3。attached、post-release、current-area N05 online/offline gates在同一epoch/map下fresh接受；N05 summary 14/14通过。完成30仿真秒no-goal hover、独立N07 11/11、ULog 12/12、ROS graph三个快照和最终landed/disarmed。支架helper的fresh DISARMED错误、exit1及remove-service ack缺失均原样保留；独立readback确认fixture absent、PX4 DISARMED/landed。完整结果见[证据](../../progress/evidence/n07-no-goal-hover-20261024-182.md)。

N07.29 #183：同一固定版本的新cold start，保留已修正的`vehicle_arming_state`读取、fail-fast顺序和ready marker后单次明确2秒settle gate。任一定位／新鲜度／安全前置失败立即停止飞行流程；成功后连续计数2/3。
