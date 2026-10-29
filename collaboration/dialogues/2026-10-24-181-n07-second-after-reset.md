# N07 #181 对话摘要：重置后的第二次连续悬停冷启动

## 用户约束

- 继续用户已授权的 N07 Goal 完成模式，直至 N07 出口通过。
- 地下不是飞行空间；保持现有 raw-ground boundary 与 N05 阶段规则，不将地下 unknown 放进空中可飞体积，不改门限。
- 前置失鲜、身份变化或准入失败时 fail-closed；不得解锁或起飞。

## 执行决定

#180在attached、DISARMED状态下于ready marker后等待2.000070387秒，随后完成N05三阶段gate、30秒无目标悬停和独立11/11验收，成为重置后的1/3。#181使用全新container和epoch，保持#180的固定版本及两秒settle，不改任何门限；所有gate通过后才执行悬停。支架helper的fresh DISARMED错误继续原样记录。证据与计划见[#180报告](../../progress/evidence/n07-no-goal-hover-20261024-180.md)和[执行卡](../../progress/changes/2026-10-24-181-n07-second-after-reset.md)。

## 结果与下一项

#181未飞行并按N07失败记录。初始attached N05只读gate fresh接受，但随后明确2秒settle后的attached gate在120秒内因`localization_not_tracking`未就绪。ready marker读取曾因字段名错误跳过第一份显式等待；shell未fail-fast，错误继续到只读gate，执行偏差已记录。定位之后转为state 4/invalid、`telemetry_stale`。支架12/12完成并安全释放，PX4保持DISARMED、landed，fixture absent，容器Exited(0)。N07计数为0/3。

N07.28 #182使用新container/epoch，固定镜像、contract、spawn、wall布局与profile不变。按marker真实字段确认attached、`vehicle_arming_state=1`和无真值/控制；启用`set -e`，明确等待2秒后仅运行一次attached live/offline N05 gate。若tracking/freshness任何条件失败，立即安全释放并停止；不在同epoch反复检查以等待健康恢复。通过后继续post-release/current-area gates，再执行30秒no-goal hover和独立N07评估。详细证据见[失败报告](../../progress/evidence/n07-preflight-localization-failure-20261024-181.md)和[执行卡](../../progress/changes/2026-10-24-182-n07-repeat-after-localization-gate.md)。
