# N08 #299 接触面未知拒绝

- 用户授权：继续完成 N08；简单目标到达后停止，返航属于另一条命令。
- 本轮范围：新冷启动 motion-cancel 前置 N05 raw-map 检查。
- 结果：全机支架路线状态 6/6 且夹具移除，但 helper 留有 DISARMED freshness 错误，不能记为扫描通过。释放后接触面 N05 有 24 个 unknown voxel center，均在有效拟合地面 z=−0.35 m；在线／离线同样拒绝。HOLD unknown=0。没有 mission、goal 或 flight。PX4 未解锁且 landed，bridge DISABLED、控制输出为 0，容器停止 exit 0。
- 决定：只改变下一轮 N05 profile，采用已有 `n08_overhead_free_sector_view` 获得俯视／侧向地图观测；所有 admission threshold、机体包络、布局及 N08 速度门不变。若 N05 仍拒绝，不执行飞行。
- 待做：#300 新鲜 N05 准入；随后完整 motion-cancel 停稳／落地；冻结身份后的 3 次独立普通 terminal-stop。
