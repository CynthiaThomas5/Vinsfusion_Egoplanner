# N08.2ak #248：减慢首段下降仍在同一高度附近触发代价锁存

## 假设与唯一变量

基于 #247 的负 Y profile，仅把首段 z=1.0→0.5 m 下降由 8 s 延长到 20 s，期望减轻新增负 Y 观察后垂直运动带来的 VINS 代价越门。视角、planner、地图规则和全部健康／速度阈值不变。

## 结果

负 Y 观察与回中完成；首段下降期间仍触发 `normalized_cost_exceeded`，末次归一化代价 1.037158。触发 health snapshot 的 optimized/telemetry 源龄分别约 64/68 ms，`stale_observation=null`，prior evaluation 与 spectrum 检查通过。PX4 HRT／ROS 在结束读回仍为 38/38 有效，gap −4…+8 ms。减慢首段下降没有解除拒绝；不再重复调整同一段时长。

比较同一下降高度附近：#247 在 z≈0.76 m 附近代价约 0.997 并越门；#248 延长到 20 s 后，在 z≈0.8 m 附近仍上升到门限以上。#246 没有新增负 Y 观察时，同高度首段下降 cost 约 0.71。不同 epoch/运行不能单独证明视角因果，但这些迹象不支持继续只调下降时长。

#248 没有 post-release gate，故没有同图 map/hold unknown 数；compute-only、曲线证书、XY 与制动测量均未运行。helper 确认 fixture detach/removed 和 landed；新鲜 PX4 probe 确认 DISARMED、landed、bridge `DISABLED`、控制话题零样本；容器安全停止 exit 0。N08 仍 `in_progress`。

## 下一步

沿用 #233 已完成 N05 的 negative-only profile `n08_overhead_negative_side_view`，在当前 fresh run 上替换 combined positive+negative 侧视序列。假设是避免同一 scan 中两种侧视叠加导致的高代价，同时仍针对 #246 的负 Y unknown。#233 的地图来自另一 epoch，不能代替本次 same-identity gate；本 run 必须重新取图并按原阈值证书判断。

## 产物

完整记录位于 `artifacts/runs/n08-20261024-248-negative-y-slow-descent/`；fixture、stage、trace、VINS 和最终 safety 文件的哈希见同目录下方 JSON 摘要。
