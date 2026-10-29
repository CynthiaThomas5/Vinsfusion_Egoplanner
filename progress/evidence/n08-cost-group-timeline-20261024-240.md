# N08.2ad #240：返程 cost 分组和时间线

## 范围

只扩展只读 source observer：保持原有 100 ms telemetry 采样，额外记录 normalized cost、visual/IMU/marginalization 组成本、cost 分组校验和压缩 prior 摘要；每次进入或退出 1.0 门限时立即补记。控制、路线、健康门限和 PX4 时间逻辑不变。

Run：n08-20261024-240-cost-group-timeline-01

## 结果

- N05 before online/offline 同身份拒绝 ground_plane_insufficient_raw_occupied_voxels。DISARMED 支架扫描第 16/22 段因 normalized_cost_exceeded 中止；没有 after/post-release admission、compute-only、goal 或 XY。
- 新 observer 采到 4046 条 telemetry 汇总。第一个超限样本 stamp_ns=483848000000，normalized_cost=1.002603487；此前一条为 0.999406813。超限记录共 9 条，首末跨 1.056 仿真秒，最高值 1.015816469。失败不是只出现一次后立即稳定恢复的孤立记录。
- 第一条触发消息的 adapter Health.metrics 与同戳 raw VINS telemetry 的 final_cost/residual_components 精确相同；原公式 cost=1.002603487。
- 第一个 crossing 的分组：marginalization 1451.181（69.8%），IMU 256.611（12.4%），visual 369.986（17.8%）。分组和误差 4.55e-13；prior evaluation/spectrum 和 76/76 rank 检查通过。这个结果定位了该帧最大的 cost 组，不识别 prior 内哪些历史测量产生残差。
- VINS_DIAGNOSTIC_COST_GROUPS=1 是一次性模式，按既有诊断补丁仅在首次过阈值时求分组，因此只有第一帧有分项；本轮没有改成 continuous，避免未评估额外诊断开销。
- nearest fixture joint trace 在该 source time 附近显示 yaw=-2.851 rad；其 LocalizationStatus 回读 8 ms 后仍 valid/cost=0.996173，比 raw estimator metric 慢一拍。这说明 runner 状态 trace 不是 cost 指标的精确采样时刻。
- PX4 bridge 3998 个样本的 HRT/ROS /clock gap 为 -8…16 ms，时间域无无效样本、无 bridge timestamp error、无 clock 回退。最大 pair gap 42.780s 在定位锁定后增长。
- cleanup helper 确认夹具 detached、Gazebo model absent、PX4 landed 和 state=DISARMED，但本身缺 fresh status 回读；随后只读 PX4 CLI 再确认 DISARMED、landed、ground contact、at rest。project.sh stop 后容器 exited 0。
- PX4 log 的 IMU duplicate timestamp 行单独保存在 JSON 证据，不据此归因这次定位质量锁定。

## 验证与限制

- 58 项定向单测通过；runner shell syntax、AST、JSON 和 git diff check 通过。
- cost/prior 离线 validator 在锁定帧通过。
- 完整 100 ms observer timeline、输入清单、raw telemetry、fixture trace、health snapshot 与 safety readback 位于 artifacts/runs/n08-20261024-240-cost-group-timeline-01/；哈希见 JSON 报告。
- 父 N08 仍 in_progress。PX4 时钟错位未复现；该路线的定位质量门仍会触发。下一步使用已有 N05 通过的 n08_overhead_free_sector_view 路线获取新鲜同身份地图，再走既有 compute-only 和停止包络门；不执行 XY，直到停止边界有实证。
