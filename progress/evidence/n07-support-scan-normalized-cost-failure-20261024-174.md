# N07 #174：pitch 转入期间单帧 normalized-cost 越线

## 结论

#174 在 `oblique_separated_return` 支架扫描第 4/12 阶段、pitch 转入约 0.45 rad 时，VINS 一个 telemetry 样本的 normalized cost 升至 1.162528，定位按现有健康规则锁存 `normalized_cost_exceeded`。该样本前后相邻值分别约 0.3557 和 0.3304；solver 仍报告 usable，bias 峰值仅 0.01568 m/s²。只读 freshness 时间线没有发现此前 raw VINS 源时间断档：raw telemetry 与 raw odometry最大 source gap 都为 0.096 s，且在失效后继续发布。失效后适配 odometry停止、status持续报告锁存错误，因此本次不是“源数据 stale 导致 adapter 停发”的证据。

扫描仅完成 4/12，没有 attached 或 post-release N05 gate、解锁、飞行或悬停。fixture 已安全 detach 并移除，PX4 保持 DISARMED/landed，容器正常退出。N07连续合格数仍为0/3。

## 运行身份与准入

- Run `n07-20261024-174-01`，epoch `4b8cfabbafa54ad8a7bed0652662de89`；固定镜像 SHA-256 `099ab9afecd28b7354f6d6494944b1db30c7c67c973e9b93b03f87aca7ad6f8`，runtime contract SHA-256 `856bf1f2222a5286493813c9702731f7e5166844eb2bfd98c6f525f3f36924eb`。
- `wall_box_column`，spawn `-6.5,0,0.3,0,0,0`，profile `n06_full_airframe_retreat_240_oblique_separated_return`；运行输入、健康门与 N05 阈值未改。
- 初始 online/offline N05 一致拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`。没有 attached-ready marker；gate 未通过时没有飞行。

## 时序与健康事件

只读 probe 覆盖 378.4 墙钟秒，记录19,529个事件，`publishes=[]`。原始 VINS telemetry/odometry 与双目、IMU、`/clock` 在约304.3仿真秒时仍新鲜；raw telemetry/odometry的最大 source gap 为0.096秒，双目最大source gap为0.068秒。首个定位失效 status 的clock/header stamp为220.508秒，它引用的estimator telemetry stamp为220.408秒，normalized cost为1.1625276396。该样本final cost为2958.36895、residual components为4378；上一telemetry样本（220.276秒）cost为0.35570，下一样本（220.476秒）为0.33042。该次solve为0.01887秒，long tracks为102、stereo features为131，accel bias为0.00822 m/s²。

健康事件发生在pitch stage开始于211.864秒之后约8.544秒。status以`normalized_cost_exceeded`、state 4持续发布至probe结束；raw VINS源仍继续，而`/localization/imu_odom`与`/localization/optimized_imu_odom`在锁存后不再更新。健康门按现值fail-closed，本报告不把相邻样本恢复解释成可忽略该锁存。

离线对照：同一分离返回profile的#138 wall、#148 corridor支架扫描在pitch阶段最高normalized cost分别约0.773、0.823；当前组合的#173为0.665（之后pitch复位阶段0.708），均未越线。#174因此是一次单样本尖峰，现有证据不能确定其上游原因，也不能归因为probe的计算负载。VINS求解耗时未见明显增大：#174失败阶段P95约0.0210秒；#173完整pitch阶段约0.0212秒。相比结果支持“本次是估计代价突升而非源龄断档”，但不证明其成因。

## 安全收尾与局限

runner记录 `verified_detached=true`、fixture已移除、`final_landed=true`、landed detector=true、PX4 vehicle state `[1]`。初始N05检查记录bridge DISABLED；容器`Exited(0)`，无活动项目容器。没有修改源码、配置、阈值或准入规则。

本次没有测到N05 attached/released正向门，也没有N07飞行出口；#173的`telemetry_stale`首发原因仍不能由#174追溯。完整原始数据及哈希见同名JSON和`artifacts/runs/n07-20261024-174-01/`。
