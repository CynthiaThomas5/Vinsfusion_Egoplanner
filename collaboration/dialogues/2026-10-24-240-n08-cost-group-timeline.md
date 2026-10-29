# N08.2ad #240 对话摘要

- 用户关注 N07 非连续累计通过是否合理，以及 PX4 时间错位会不会堵住后续。#198/#200/#204 保留为 N07 3/3，不复测。
- #239 已用 Health.metrics 同戳回读确认真实 cost 锁定；本轮在只读 100 ms source observer 增加 group cost 和 cost-limit transition 采集。58 项定向测试通过。
- #240 的 N05 before 仍拒绝 ground_plane_insufficient_raw_occupied_voxels；support scan 第16/22段触发 cost=1.002603487。锁定帧与唯一同戳 raw telemetry 精确一致。
- 总计 9 条 telemetry 在约1.056 sim s区间内超过1.0；首帧 marginalization 69.8%、IMU 12.4%、visual 17.8%，prior evaluation/spectrum和76/76 rank checks通过。不能由这些数据直接指出 prior 中哪条历史测量导致残差，也不提高门限。
- VINS_DIAGNOSTIC_COST_GROUPS=1按既有行为只求首次 crossing 的分项；没有启用持续分项模式。
- PX4 HRT/ROS /clock −8…+16 ms，3998 bridge samples全部time-domain valid，没有bridge timestamp error或clock regression。pair gap在定位锁定后上升。
- helper 清理需fresh状态监护；实时VehicleStatus/VehicleLandDetected确认DISARMED、landed、at rest，fixture model absent，project.sh stop exit0。
- 下一步为 fresh map/compute-only 使用此前已通过N05的 n08_overhead_free_sector_view；stop envelope通过前不做XY。
- 证据：[N08 #240 报告](../../progress/evidence/n08-cost-group-timeline-20261024-240.md)。
