# P4 导航 action 与 EGO 取消接口

对话摘要：[2026-10-17-020](../../collaboration/dialogues/2026-10-17-020-p4-navigation-ego-action-cancel.md)

## 改动

- 新增 `NavigateToPose` action、`NavigationCommand` 与 `TrajectoryCancel` 消息；`PositionCommand` 添加 `goal_id` 和 `epoch`。
- `uav_navigation.node` 增加 ROS action adapter 与 launch 入口。接单和实际投递前都核对当前 epoch、TRACKING、新鲜定位／里程计及 EGO 端点；目标替换、显式取消、定位失效和时钟回退按任务键通知 EGO 与轨迹服务器。
- EGO FSM 接收指定三维位置和 yaw，并在普通、重规划、急停及 swarm B-spline 中保留任务键；`traj_server` 用 epoch frame 发布采样轨迹，采样目标 yaw，只响应匹配取消，并通过既有唯一 `/position_cmd` publisher 发 ABORT。
- EGO 改动记录在 [patch 0017](../../dependencies/patches/ego/0017-task-goal-epoch-and-cancel.patch)，SHA-256 `e82a26df1d5a1113e7b19b3e8556f81ef2bc09cf07db5670f3094e9afad68dc1`。

## 验证

- 在固定 Jazzy 容器的新 build/install 路径执行 `colcon build --base-paths src/own src/vendor/ego_planner/planner --packages-up-to uav_navigation ego_planner --parallel-workers 2`：7/7 包通过；新增代码后又增量重建 `uav_navigation`，通过。
- `python3 tools/test_navigation_task_state.py`：9 项通过。
- `python3 tools/test_navigation_adapter.py --project-root /workspace`：通过，覆盖 action 路由、显式取消、旧 epoch 拒绝和 clock regression abort。
- `python3 tools/test_trajectory_server.py --traj-server <fresh-install>/ego_planner/lib/ego_planner/traj_server`：通过，覆盖 yaw 样条、epoch frame、陈旧取消忽略、匹配取消 ABORT 和进程正常退出。
- `ros2 launch uav_navigation navigation_supervisor.launch.py --show-args`：launch 文件可解析并显示 `project_root` 参数。
- `git diff --check` 与 `python3 tools/project_status.py`：通过。

完整命令、日志、二进制哈希与合成验收范围见 [P4 action/取消证据](../evidence/p4-navigation-ego-action-cancel.json) 和 `artifacts/runs/p4-navigation-ego-wire-20261017-01/`。

## 限制与下一步

ROS action 测试使用合成定位／里程计和 fake EGO endpoint；轨迹采样测试直连真实 `traj_server`，没有启动 EGO FSM、VINS、地图、PX4 或控制器。Fast DDS UDPv4 仅用于规避本容器已记录的 shared-memory 诊断问题，不是项目默认参数。EGO 在线规划、避障、轨迹跟随、PX4 bridge、安全降落和真值隔离均未验收。下一步在动态 D435i/VINS/EGO 场景中验证目标规划与目标 yaw，再补齐唯一 PX4 控制出口和 SITL 闭环。
