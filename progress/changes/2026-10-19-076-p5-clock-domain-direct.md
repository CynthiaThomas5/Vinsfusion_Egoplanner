# P5 PX4 Gazebo lockstep 时钟域与被动 SITL #194

对话摘要：[2026-10-19-076](../../collaboration/dialogues/2026-10-19-076-p5-clock-domain-direct.md)

## 修改

- 在 PX4 bridge 时间映射中加入 lockstep direct-sim-time 路径：关闭 XRCE Agent 时间同步时直接用 `/clock` 域处理 PX4 telemetry 与 VIO 时间戳，不以 Agent wall clock 作为静默回退。
- bridge 的 timesync 订阅和 freshness 检查按配置启用；readiness 使用 `px4_time_domain_valid`，PX4 控制发布者仍只有 bridge。
- 将 `UXRCE_DDS_SYNCT=0` 加入 PX4 debug SITL 参数，并由参数 staging 与 `project_status.py` 检查其和时钟配置一致。
- live probe 增加 `--direct-sim-time` 与 PX4 原始时间戳相对 `/clock` 的采样记录。

## 结果

- #194 使用固定 PX4 commit `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`、镜像 `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`，PX4 ULog 验证 `UXRCE_DDS_SYNCT=0`、`UXRCE_DDS_SYNCC=0`。
- 被动运行20秒，attitude 与 local-position 原始戳对 `/clock` 的最大绝对差分别4 ms、8 ms；bridge detail 的 telemetry 源龄全部非负，`px4_time_domain_valid=true`。
- bridge 155 条状态均为 DISABLED/`localization_not_tracking`；timesync status、VIO、Offboard、trajectory、vehicle-command 样本数均为0；无 debug_truth 订阅，车辆保持 disarmed。
- PX4 官方 ROS 2 指南建议 ROS 使用 Gazebo `/clock` 时关闭 `UXRCE_DDS_SYNCT`；该建议与本轮观测一致，但 full VIO workload 仍待验证。

## 验证与限制

- `test_px4_bridge_time_mapping.py` 18项、`test_px4_bridge_control.py` 11项、`test_px4_bridge_vio_profile.py` 7项、`test_px4_debug_params.py` 2项、`test_px4_bridge_frames.py` 19项通过。
- Jazzy `colcon` 新目录构建 `uav_px4_bridge` 所需自维护包6/6通过；Python `py_compile` 与运行脚本 `bash -n` 通过。
- `python3 tools/project_status.py`、JSON/hash 检查与 `git diff --check` 通过。结构检查仅说明仓库骨架一致。
- 本轮没有 VINS、定位、地图、导航目标或飞行；readiness 因 localization 未启动而为 false。P5 仍进行中，所有门限保持不变。下一步先被动运行完整 VIO 图，再评估是否重做有效 no-motion 对照。
