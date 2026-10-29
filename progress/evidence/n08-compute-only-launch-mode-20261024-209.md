# N08.2a #209：EGO 计算、bridge 保持模式接线

## 结果

新增了一个仅用于 N08 对照的 launch 开关 `bridge_compute_only`。开启时，EGO 仍向 `/position_cmd` 发布曲线，观测节点仍可记录这些消息；只有 PX4 bridge 对 `/position_cmd` 的订阅被重映射到无发布者的 `/n08/compute_only_position_cmd`。因此 bridge 状态机没有看到活动曲线，会按现有逻辑继续输出 hold。关闭时不应用 remap，维持原执行路径。

`tools/project.sh sim` 现在可通过 `D435I_BRIDGE_COMPUTE_ONLY=true|false` 与 `D435I_PLANNER_CONFIG=<project-relative-json>` 显式选择模式和 planner 配置；主机侧、容器侧均校验开关值，planner 路径限定在项目目录。每个 VIO/EGO 启动在 stack run 目录记录 `n08-runtime-mode.json`。计算模式不会创建第二个 PX4 控制发布者，也未更改桥接器控制 topic、N05 包络或任一健康阈值。

## 验证

- `tools/project.sh build ros`：17 个 ROS 包完成。
- `tools/project.sh test`：281 项通过，`test_navigation_adapter.py` 通过。
- `python3 -m py_compile ...vio_closed_loop_ego_px4.launch.py ...vio_closed_loop_px4.launch.py`：通过。
- `bash -n tools/sim_runtime.sh tools/project.sh`：通过（含新环境输入检查）。
- 在固定容器镜像里分别运行两个 launch 的 `ros2 launch ... --show-args`：父／子 launch 均声明 `bridge_compute_only`，默认 `false`；通过。
- `tools/project_status.py` 与 `git diff --check`：通过。

## 限制与后续

本项没有启动 Gazebo、PX4、起飞或平移；没有运行时 ROS graph 证据，也没有证明取消行为或 hold 控制性能。它只提供受控模式接线。下一子项 N08.2b 是显式发送目标、捕获 READY 曲线、立即取消并确认 bridge 仍 hold 后安全落地的诊断 runner。运行期验证仍须使用独立启动、当前 N05 入口准入；实际平移继续被制动边界和已知停止走廊 gate 阻断，不能用本项通过替代。
