# P2 当前 EGO/VINS 负计时复测与时钟偏移监测 #286

对应对话摘要：[2026-10-20-043](../../collaboration/dialogues/2026-10-20-043-p2-vins-clock-offset-repeat.md)。轻量证据：[p2-ego-current-vendor-clock-monitor-20261020-286.json](../evidence/p2-ego-current-vendor-clock-monitor-20261020-286.json)。完整采集、离线分析和逐文件SHA-256见 `artifacts/runs/p2-ego-current-vendor-clock-monitor-20261020-286/`。

## 结果

- 以当前固定 VINS/EGO 运行组合重复planner-only目标；5.715秒派发目标，MapStatus ready、902个占据点，捕获27条三阶B-spline。离线首条固定尺度SE(3)位置RMSE 7.47 mm、P95 13.21 mm，已知箱体／圆柱名义球余量0.554/1.639 m。这些是描述性规划诊断，不构成地图覆盖、净空或轨迹执行验收。
- VINS telemetry 644条、解析错误0；本轮未出现负 `solve_seconds`，最大正值10.56 ms。主机在85.387秒内取得8470个realtime-minus-monotonic样本；偏移变化范围17.713 μs，最大相邻变化17.432 μs，未观察到明显向后跳变。
- 后续定位于52.862秒因 `normalized_cost_exceeded` 锁定，锁定点cost 1.0034，全轮最大1.1132；这与#284的负求解时长触发不同。EGO仍记录19条输入同步超时日志；没有证据把它们与本次定位质量门联系起来。
- 官方Ceres 2.2.0源码以 `WallTimeInSeconds() - start_time` 计算总时间，Linux实现使用 `gettimeofday`；因此realtime时钟倒退是负时长的一种可能机制，但#284没有同钟监测，#286也未复现，根因仍未确定。
- 运行图未发现控制节点或控制话题；没有PX4、轨迹服务器、控制器或运行时真值源。

## 修改与验证

- 本轮只新增运行报告、离线诊断、证据索引和项目进度记录；未修改VINS/EGO/自维护源码、健康阈值或运行参数。
- #286采集脚本退出码0；运行报告列出的原始采集文件及分析报告SHA-256复核通过。
- `python3 tools/project_status.py`：待本轮收尾执行；静态证据索引不代表构建、SITL或飞行验收。

## 状态与下一步

P2阶段表状态保持passed；GOAL A–H状态未改变，P6仍进行中。健康门及 `max_solve_s=0.1`、`max_normalized_cost=1.0` 保持PROVISIONAL且未变。下一步在run-local VINS副本中增加独立 `steady_clock` 求解耗时字段，保留原始Ceres wall-time字段，在同类运行中对照两者及主机时钟偏移；不把实验计时接入正式门控。随后继续处理EGO输入同步、free/unknown与覆盖证据，并推进正式D/E/F验收。
