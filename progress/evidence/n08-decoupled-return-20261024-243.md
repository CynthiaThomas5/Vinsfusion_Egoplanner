# N08 #243：分离 yaw/pitch 返回顺序

## 结果

父 N08 仍为 `in_progress`。新增的 16 段 profile 完成 14 段；在 N05 post-release/current-area gate 前发生 `normalized_cost_exceeded`，没有运行 compute-only mission。

初始 N05 online/offline 同身份检查一致拒绝 `ground_plane_insufficient_raw_occupied_voxels`。DISARMED 支架扫描的 yaw 与 pitch 返回已拆开，分别完成后继续到最后的垂直回程；在该回程阶段，健康节点记录精确锁定快照：source stamp `416956000000 ns`、normalized cost **1.013032**（门限 1.0）、final cost 2421.912／4720 residual components。最近 fixture pose 为 sim 416.824 s，z joint 0.3703 m，profile 正在从 0.5 m 回到 0 m。

分组占比：imu 5.1%, marginalization 49.7%, visual 45.2%。分组求和通过；marginalization prior evaluation、spectrum 与 rank（82/82）检查通过。这说明把 pitch/yaw 分开后仍有轻微越限，并且触发发生在之后的垂直回程；当前证据不支持将根因只归结为 yaw/pitch 同步动作，也没有识别出单个残差的根因。实时 `vio.log` 中的健康快照是触发依据；fixture VINS 抽样未包含同一越限样本，不能拿它的最大值替代该快照。

触发样本各来源 age：imu 0 ms, left 20 ms, optimized 60 ms, propagated 0 ms, right 32 ms, telemetry 68 ms。PX4 HRT 对照 observer 未在本 run 启用，因此不单独给本轮 PX4/ROS 时钟结论。#237–#240 已有的 PX4 时间域对照仍显示毫秒级、有效的时间关系。

fixture detach/remove 有确认。fresh PX4 readback 为 DISARMED、landed、at rest，bridge `DISABLED`；`tools/project.sh stop` 后容器 exit 0。没有 post-release admission、compute-only、goal、XY 或制动数据。

## 证据

- 原始 run：`artifacts/runs/n08-20261024-243-overhead-free-sector-decoupled-return/`
- 机器报告及 SHA-256：[JSON](n08-decoupled-return-20261024-243.json)
- 过程记录：[change record](../changes/2026-10-24-243-n08-decoupled-return.md)
