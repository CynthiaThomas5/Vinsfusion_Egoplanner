# P2 定位状态与会话适配

- 任务 ID／日期：007，2026-10-16
- 对话摘要：[P2 定位适配与真实回放](../../collaboration/dialogues/2026-10-16-007-p2-localization-adapter.md)
- 修改文件：`src/own/uav_interfaces`、`src/own/uav_localization`、`config/components/localization/health.json`、`docs/contracts.md`、`docs/vins-debug.md`、`tools/test_localization_health.py`、`tools/probe_localization.py`、`tools/project_status.py`、README 与进度文件。
- 行为变化及原因：增加 epoch/session 固定、VINS 输入健康状态、时钟回退与数据过期锁存、VINS ROS graph endpoint identity 检查；TRACKING 时适配优化和 IMU 传播位姿，世界速度旋入 D435i IMU child frame。无飞机安装外参和上游协方差时不输出 base_link、TF 或控制，也不宣称 covariance 有效。
- 验证类型：结构、静态逻辑测试、Jazzy colcon 构建、真实 VINS 录包回放。
- 命令与环境：`python3 tools/test_localization_health.py`；Jazzy 容器 `colcon --log-base artifacts/runs/p2-localization-adapter-replay-20261016-05/log build --base-paths src/own --packages-select uav_interfaces uav_sim uav_localization --build-base artifacts/runs/p2-localization-adapter-replay-20261016-05/build --install-base artifacts/runs/p2-localization-adapter-replay-20261016-05/install`；重放 `artifacts/runs/p2-force-motion-20261016/input-bag`，ROS_DOMAIN_ID 87。
- 结果及证据位置：8 项逻辑测试通过；3 包真实构建通过；适配器真实回放进入 TRACKING，约15.15 Hz 优化与200 Hz传播输出单调有限；录包停止后锁存 `imu_stale`，之后3.016秒无新增输出。另一次 VINS 停止／相同 epoch 重启注入后状态仍锁存，重启后3.017秒未输出新里程计。详见 [P2 适配证据](../evidence/p2-localization-adapter.json)、`artifacts/runs/p2-localization-adapter-replay-20261016-05/` 和 `artifacts/runs/p2-localization-vins-restart-20261016-06/`。P2 保持 in_progress。
- 未验证与 PROVISIONAL：当前健康阈值并非正式冻结验收标准；单次回放不是独立精度复测；相机／IMU／深度故障、第二次 VINS 重启／端点切换、时钟回退的 ROS 进程注入未完成；VINS failureDetection 仍禁用；未接地图、EGO、PX4 或 EKF2。
- 下一步：校准健康门槛并独立复测，按 GOAL.md 做故障重复注入；同时继续 P0 依赖冻结与 P1 飞机安装校准。
- 当前源码 SHA256：见 `progress/evidence/p2-localization-adapter.json`；无提交。
