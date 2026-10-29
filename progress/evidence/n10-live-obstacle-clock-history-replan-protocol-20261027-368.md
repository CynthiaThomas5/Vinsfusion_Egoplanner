# N10.3/#368：扩大 PX4 时间映射历史窗口后复测动态障碍

## 假设与唯一变量

#367 在仿真 129.264s 收到一个源时间为 128.968s 的合法 VIO 样本，源龄 0.296s。bridge 当时的映射缓存仅 64 个 `/clock` 样本，样本时间早于缓存最早时刻而被报 `source_stamp_outside_clock_history`；对应墙钟龄 0.345s，仍低于配置的 0.35s 源龄上限。唯一变量是将 `clock_mapping_max_samples` 从 64 增至 128，不放宽源龄、里程计接收龄、PX4、EGO 或碰撞限制。

## 固定输入

- Runtime contract：`68aba197b9db4e6a405baaaafccdcec91ba91434e3525f56b701f9c5a6772734`（665项）。
- EGO 补丁0053和binary与#367保持一致；17包构建日志见 `artifacts/runs/n10-20261027-366-ego-patch-build/build.log`。
- Goal、spawn、planner、单箱模型、注入触发与观察器均复制#367冻结工具。
- 动态障碍为世界坐标(0,0,1.4)m、尺寸0.8×0.8×2.8m；目标为16m单程。
- 不属于N11/N12正式资格。

## 运行判据

检查时间映射是否能接纳源龄不超过0.35s且落在128样本历史内的合法数据；仍须拒绝源龄超过0.35s、时间倒退、错误epoch或无效PX4融合。随后检查箱体确认、表面观测、同一goal/epoch的绕行轨迹、真实PX4执行、到达、全机净空、零违规接触和落地读回。失败保留；不得通过放宽其他门限判成功。

## 冻结

协议JSON SHA-256：`f6a3aac6284032600e7de41752653beaa727e5549acd0ae8985563cff3b63f12`。运行ID：`n10-20261027-368-clock-history-live-obstacle`。启动前身份见 [prelaunch JSON](n10-live-obstacle-clock-history-replan-prelaunch-20261027-368.json)。
