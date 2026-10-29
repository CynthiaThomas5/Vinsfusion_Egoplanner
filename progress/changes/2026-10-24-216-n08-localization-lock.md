# N08.2f #216：支撑扫描与 localization stale 锁存诊断

- 新启低负载只读 recorder 记录 VINS telemetry/raw odometry、optimized odometry、`/clock` 与 LocalizationStatus。运行脚本保存在对应 run artifacts；仓库源码、运行参数、健康门和 PX4 控制实现均未改。
- 支撑扫描完成 12/12；释放后和 current-area N05 online/offline gate 通过。扫描段 source/clock 年龄保持新鲜。
- compute-only 未起飞：mission runner 观察到 `localization_not_tracking`／`telemetry_stale`，fail-closed 写入 `flight.json`。故障后的回读显示 raw VINS stream 已新鲜，但 adapter status source stamp 冻结，说明 stale 锁存持续存在；首次锁存窗口仍未捕获。
- 已停止容器；`project.sh stop` exit 0。证据：[N08 #216](../evidence/n08-localization-lock-20261024-216.md)。对话摘要：[2026-10-24-216](../../collaboration/dialogues/2026-10-24-216-n08-localization-lock.md)。
- 下一步 #217：同一轻量记录器从支撑扫描前持续到 N05 与 compute-only readiness 结束，抓 stale 首次转换；若进入 PRESTREAM 则先停 observer。不复测 N07 通过项。
