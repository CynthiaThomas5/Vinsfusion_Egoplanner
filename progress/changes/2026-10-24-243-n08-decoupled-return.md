# N08 #243 分离姿态回程诊断

## 改动

- 新增 `n08_overhead_free_sector_view_decoupled_return` N05 profile：保留原前段与场景，仅把 yaw/pitch 联合回中拆成先 pitch 回中、再 yaw 回中。
- 新增 profile 结构测试和 runner allowlist。未改健康阈值、导航目标、控制或 N08 验收标准。

## 验证与运行

- `python3 -m unittest tools.test_preflight_scan`：32 tests 通过；`bash -n tools/run_n05_preflight_layout.sh`、profile JSON、`git diff --check` 通过。
- Run `n08-20261024-243-overhead-free-sector-decoupled-return`：N05 before online/offline 一致拒绝 ground_plane_insufficient_raw_occupied_voxels；支架扫描 14/16 后在 stage 15 垂直回程 `normalized_cost_exceeded`，精确健康快照 1.013032。visual/IMU/marginalization cost 组为 imu 5.1%, marginalization 49.7%, visual 45.2%；prior rank/spectrum 检查通过。
- fresh PX4 状态 DISARMED/landed/at-rest，bridge DISABLED；fixture removed，容器 stop exit 0。
- 无 post-release N05 gate、compute-only、goal 或 XY。

详情：[证据](../evidence/n08-decoupled-return-20261024-243.md)；[机器报告](../evidence/n08-decoupled-return-20261024-243.json)。
