# P2 EGO 建图输入间隔诊断

日期：2026-10-17

- 用户约束：继续按 GOAL.md 推进 P0–P6；保护既有暂存和未提交修改；不启动 PX4 控制。
- 发现：run #12/#15 的故障前配对输入 p95 间隔均为0.132 s，最大值为0.231/0.264 s。run #14 在22.408 s最后更新后，配对输入仍继续到达，而EGO约0.429 s后报timeout；由VINS位姿与SDF外参推算的相机位置在该时刻处于地图内。无故障 run #17 的40秒采样保持深度 READY、定位 TRACKING，产生470组配对输入和最多1799个占据点，但 EGO 记录25条 timeout 告警，最大配对间隔0.495 s；直接相机 Z 样本距地图下界最少约0.6 mm。
- 决定：0.4 s 保持 PROVISIONAL；run #17 是有效无故障成图观察，但 timeout 告警未关联每次输入 callback；继续检查 EGO 时钟、ApproximateTime 队列和地图下界余量，不把配对消息间隔等同于内部 GridMap 更新间隔。
- 排除：run #16/#18 的无故障尝试因定位适配器 `propagated_stale` 锁定，没有有效地图输入；run #14 因注入前 EGO 已有 occupancy gap，不计因果 stale 证据。只读 probe 已增加相机位姿和配对间隔记录；运行脚本采用隔离进程组清理。
- 待决：重复 run #17 并记录 EGO current clock、source age 与实际同步 callback 延迟；分析地图垂向边界对更新的影响，再校准阈值并重复 stale 测试。
