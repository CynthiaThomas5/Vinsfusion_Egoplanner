# N07 #202：右图像输入 stale 导致起飞前拒绝

## 结果

**FAIL_PRECONDITION；连续通过数保持 0/3。** 独立冷启动目录：[n07-20261024-202-01](../../artifacts/runs/n07-20261024-202-01/)。N07 仍为 `in_progress`。

no-goal runner 因 `vio_bridge_map_preconditions_not_ready` 在起飞前退出；`LocalizationStatus` 为 `state=4, valid=false, reason=right_stale`，bridge `DISABLED`。没有发送 goal 或起飞命令，没有进入 ACTIVE/armed，也没有悬停。

## 固定条件与 N05 结果

运行保持固定镜像 `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`、runtime 配置 SHA-256 `1ddd6838ae2a678f89547ce90eea849582edcc29cddab341667bd2d1d9d3e360`、runtime-contract 文件 SHA-256 `856bf1f2222a5286493813c9702731f7e5166844eb2bfd98c6f525f3f36924eb`、spawn `-6.5,0,0.3,0,0,0`、`wall_box_column` 与 `n06_full_airframe_retreat_240_oblique_separated_return`。原门限未改，也未启动可选 freshness probe。

初始 N05 online/offline gate 一致拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`；这只是地面接触／起飞边界的准入检查。支架路线完成 12/12，N05 summary 14/14，扫描后、post-release、current-area online/offline gate 均接受 `all_entry_phases_known_and_clear`。current-area snapshot/source/fusion age 为 0.108/0.140/0.040s，均在 0.4s 限值内。fixture helper 的 `outcome=failed` 和 `localization changed or became invalid during physical scan` 错误如实保留；fixture 已 detach/remove，scene absence 与 landed 状态独立确认。fixture trace 13,203 行、单 epoch、0 条 invalid localization row。PX4 boot audit 和起飞前安全读回 11/11 通过。

## 定位状态证据

flight runner 收到的 1,201 个定位状态样本均为 `right_stale`、`state=4, valid=false`；末尾 source stamp 停在 461.196s，而仿真状态时戳推进到 525.396s。无 `/clock` 回退，也没有 `health_future_observation` 记录。VINS raw odometry 与求解 telemetry 继续到约 525.46/525.328s，solver usable、normalized cost 约 0.483；depth health 保持 valid，occupancy cloud 没有大间隔。对齐观察器收到 39 条 optimized odometry，最后 source stamp 461.112s；其后没有继续更新，raw VINS odometry 仍在推进。

这支持“定位健康门报告右图像输入 stale，随后适配器不再输出新优化里程计”；运行没有保存右图像 topic 的源时间与投递序列，无法判断 stale 的具体来源。本次没有重现 #201 的 `imu_from_future`。

Graph waiter 因 runner 结果先于 ACTIVE+armed 写出，没有活动图快照。hover evaluator 与 airborne ULog 分析因没有飞行而未执行；N05 与 boot audit 不能替代这些 N07 出口。

## 安全收尾与下一步

最终独立安全读回 11/11 通过：bridge disabled/control off，PX4 DISARMED/landed，fixture 不在场景中，无活动 flight/observer。`bash tools/project.sh stop n07-20261024-202-01` exit 0；容器 `exited 0`，活动项目容器数为 0。没有修改项目源码、配置或验收阈值。

#202 仍以失败结束，N07 连续数为 0/3。下一项 #203 继续固定条件的新独立 cold start，不放宽右图像输入健康门。

逐文件 SHA-256 与机器可读结果见 [JSON 报告](n07-preflight-right-stale-20261024-202.json)。
