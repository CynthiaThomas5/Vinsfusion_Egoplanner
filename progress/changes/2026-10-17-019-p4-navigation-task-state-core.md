# P4 导航任务状态核心

日期：2026-10-17。对话摘要：[2026-10-17-019-p4-navigation-task-state-core.md](../../collaboration/dialogues/2026-10-17-019-p4-navigation-task-state-core.md)。

- 新增可构建 `ament_python` 包 `src/own/uav_navigation`，核心位于 `uav_navigation/task_state.py`。它只接受有效 TRACKING 且 epoch 匹配的三维位置+yaw 目标；支持取消、替换、超时、旧轨迹拒绝及 position/yaw dwell 到达；定位失效、epoch 改变与 ROS clock 回退会终止目标并返回要求清除轨迹的事件。时钟回退锁定当前会话，只有观察到新 epoch 后才重新允许接纳任务。
- 输入、输出与控制权：状态核心接收调用方提供的定位状态、epoch、时钟和位姿；返回有序任务事件，不发布 ROS 控制或轨迹。`uav_px4_bridge` 唯一控制设定点发布者约束不变。
- 验证：`python3 tools/test_navigation_task_state.py` 9/9通过；固定 Jazzy 容器中新 build/install 目录 `colcon ... --packages-select uav_navigation` 通过；安装源码与工作区源码 SHA-256 一致；`python3 tools/project_status.py` 结构检查通过。命令、测试覆盖、日志与源码哈希见[证据](../evidence/p4-navigation-task-core.json)。
- 局限：目前没有 ROS action/node、EGO 目标/取消服务或 PX4 bridge；EGO 现有目标回调仍忽略 z/yaw。此增量仅证明状态策略，不构成 P4、GOAL D/E 或任务闭环通过。第三方 EGO 源码未改。
- 下一步：接入 ROS action 与反馈；在 `dependencies/patches/ego` 建立有基准的 EGO 输入/取消补丁，使其消费 epoch-bound goal 和清轨迹事件；编译后对定位 LOCKED、epoch 改变及 `/clock` 回退做 live ROS 集成测试。
