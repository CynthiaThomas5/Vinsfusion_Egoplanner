# #104 N06 wall-layout live lateral EGO curve

日期：2026-10-23。用户以`codex resume --last`恢复Goal完成模式，指定范围N06。父目标N06/S4仍`in_progress`，`next_goal=N06`。

## 约束

- 单D435i未武装传感器夹具仿真；planner-only EGO不连traj_server、controller、PX4或setpoint。
- unknown fail-closed，保留N05包络／预算与N06原出口。工作区已有修改均属用户，不回滚。

## 决定与结果

r28 snapshot raw复算证明wall起点body和terminal hold为free；其默认抬高目标hold含5个occupied voxels而正确拒绝。r29保留同一X观察profile与wall场景，在snapshot-01到02间发出`(0,+0.6,0)m` lateral planner-only目标。实际EGO发布一条goal／epoch匹配B-spline，live full-curve证书`reason=free`、45 query、0.430ms；无fault／迟到curve，control-free graph通过。fresh snapshots的raw body／hold查询和lateral straight sweep也通过。实时body query仍单次`no_fresh_fused_depth`，记录为未解决瞬时服务拒绝。详见[#104 evidence](../../progress/evidence/n06-live-ego-lateral-curve-20261023-104.md)。

## 下一步

在第二实际布局`corridor_box_column`重复同一X观察流程。通过新的snapshot进行精确body/hold/sweep检查，只在安全的后退候选目标可用时调用planner-only EGO；窄走廊内的terminal hold不能预设可用。无候选则保留no-go。N06的两布局curve、hold、handoff和故障拒绝矩阵仍未完成。
