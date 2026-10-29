# N10.3/#398 综合校准运行结果

对话摘要：[N10.3/#398 综合校准结果](../../collaboration/dialogues/2026-10-27-398-n10-integrated-calibration-result.md)。启动绑定源码修复单独记录于[变更](2026-10-27-398-n10-localization-startup-bind.md)。

按 #397 实际缺口，在修复后的当前 runtime identity 下重跑 `max_velocity=0.4 m/s` 综合校准。16 m action、3.344 sim s 联合位置/yaw 到达、15 sim s 诊断保持和正常落地上锁通过；独立末态确认 bridge disabled/zero controls，项目进程正常停止，未使用紧急 disarm。

保存了4 ms Gazebo solver-state 净空、tracking/VIO、动态障碍、地图查询/snapshot、sensor payload receipt、资源/queue 与终态记录。离散机体净空最小0.186 m、tracking P95 0.327 m；两者用于校准，未冻结阈值。snapshot 时间关系没有证明箱体 cloud 已融合；#399 八角复算发现13个实体内部 known-free voxel，raw-map 分类草案指标失败，surface 只两面有支持。故障终态和容量基准仍不足。详见[结果](../evidence/n10-integrated-calibration-result-20261027-398.md)和[#399复算](../evidence/n10-voxel-cell-classification-replay-20261027-399.md)。

运行和driver记录：`artifacts/runs/n10-20261027-398-speed040-integrated-calibration/`、`artifacts/n10-prepared/n10-20261027-398-speed040-integrated-calibration/`。本记录没有新增源码修复；实际故障校准、N10.4、隔离干净重建、受影响回归和冻结仍未完成。
