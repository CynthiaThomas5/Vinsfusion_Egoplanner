# N10.3/#367 动态障碍 SITL 结果

关联协议：[冻结协议](../evidence/n10-live-obstacle-replan-retry-protocol-20261027-367.md)；结果：[证据报告](../evidence/n10-live-obstacle-replan-retry-20261027-367.md)。

- 运行 ID：`n10-20261027-367-ego-retry-live-obstacle`；runtime `15d935eb803e76eb378aa4aa566d2d7b46b97168e2c75e7e0ee5d87878ed57a6`。
- Gazebo create ACK、occupancy表面点和同一goal/epoch后续样条均观测到；EGO在#366 patch后没有因为planner infeasibility中止。
- 目标仍以`goal_timeout`失败；bridge在sim 129.264s因`external_odometry_stale`降落。时间线将原因定位到0.296s迟到VIO样本超出64个`/clock`样本历史，尽管墙钟龄0.345s仍在0.35s映射限制内。
- 箱体全机包络采样调整净空0.982m、整场景0.205m，零违规接触。安全停止证据确认落地、解锁解除、控制关闭和零控制；容器已退出。
- `evaluate_odometry.py`因flight record缺少完整PRESTREAM-to-LANDED序列未产出JSON；arrival evaluator的落地字段也因runner失败分支遗漏为false。故本run不提供完整N10.3 calibration bundle。
- 结果为诊断失败/部分证据，不关闭N10.3。下一步#368唯一修改 clock mapping history sample count 64→128，source age / odometry age门限保持不变，然后复测同场景。
