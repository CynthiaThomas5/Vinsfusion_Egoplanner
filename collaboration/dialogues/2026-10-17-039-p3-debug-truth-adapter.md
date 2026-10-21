# P3 debug_truth 真值适配器

- 目标：把 x500+D435i Gazebo 真值接入隔离的 `debug_truth` ROS 调试通路，为后续 PX4 bridge 提供 epoch/frame 可核对的定位输入。
- 用户约束：单 D435i 仿真；真值仅限 `debug_truth`；最终视觉组合不得订阅真值；控制输出只能由 `uav_px4_bridge` 发布；不启动真机、不修改旧来源、不覆盖既有工作区改动、不暂存／提交／推送。
- 决定：Gazebo 真值 `/debug_truth/base_odometry` 的 `world`→`d435i_link` 位姿经过 adapter 后，输出 `/debug_truth/optimized_imu_odom` 的 `odom_<epoch>`→`d435i_imu_<epoch>`。仿真 D435i IMU 与 link 同位，所以 body frame 明确表示相机 IMU 原点，不声称是 x500 `base_link`。每次 adapter 重启创建新 epoch；时钟回退、输入 stale、frame/数值异常会锁定。
- 改动：新增 `uav_sim.debug_truth_adapter` 和 `debug_truth.launch.py`；桥接相机与真值数据设置 `lazy: true`（`/clock` 常开）；新增 live adapter probe、包依赖／入口、使用文档和轻量证据。
- 验证：run #18 Jazzy 新 build/install 2/2包通过；隔离 x500+D435i SITL 获得10条单调真值样本、TRACKING 和匹配 epoch/frame；四个 PX4 输入话题 publisher 均为0。run #19 静态传感器校准31/31通过，确认惰性桥在订阅时激活。13项转换、6项时间映射测试、结构检查、静态检查和 diff 检查通过。
- 边界：未运行 PX4 DDS Agent、未向 PX4 发布 VehicleOdometry 或控制、未验证 PX4 原点／航向配对、EKF2 融合、Offboard、起飞或飞行。退出时 Gazebo bridge 先停，adapter 的 watchdog 将状态锁定为 `truth_odometry_stale`，进程退出码为0；这不算干净 teardown 验收。失败的 harness 和修复过程保留在 run #10–#17。
- 证据：[P3 adapter 报告](../../progress/evidence/p3-debug-truth-adapter.json)，原始运行目录 `artifacts/runs/p3-debug-truth-adapter-20261017-18/` 与 `artifacts/runs/p3-debug-truth-adapter-20261017-19/`。
