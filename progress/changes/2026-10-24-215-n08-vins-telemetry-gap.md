# N08.2e #215：VINS 遥测 stale 失败记录

- 记录 #215 支架扫描在第 5/12 阶段因 localization `telemetry_stale` 失败；未进入 N05 释放后准入或 compute-only。
- 对 `fixture-vins.jsonl` 与 `fixture-odometry.jsonl` 计算 source stamp 间隔，并与 localization health 的 0.30 s telemetry source-age 门限对照。#211/#213 也出现超限 gap 但没有相同的最终 stale 锁存，故 gap 与 stale 的因果仍未证明；发布／传递／接收／时钟各环节的首因仍未区分。
- 明确本 run 不支持把故障归因于 PX4 HRT 时间参考；保留 N07 #198/#200/#204 已通过、不连续也不复测的决定。
- 无源码或阈值变更。安全收尾：fixture detached/removed、PX4 DISARMED、landed，项目容器已停止。
- 验证／分析命令：Python JSONL 时间戳 gap 复算；`sha256sum` 冻结本次关键产物；`docker ps` 未发现该 run 活动容器。
- 下一步：N08.2f #216 用低负载只读时间线 recorder 同步记录 source、receipt、`/clock` 和首次 stale 翻转，定位造成间隔的链路；避免启动 #192 对照中的全量可选 freshness observer。

证据：[N08 #215 遥测 stale 报告](../evidence/n08-vins-telemetry-gap-20261024-215.md)。对话摘要：[2026-10-24-215](../../collaboration/dialogues/2026-10-24-215-n08-vins-telemetry-gap.md)。
