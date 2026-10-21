# P4 动态 EGO 规划与仿真时钟对齐

对话摘要：[2026-10-17-021](../../collaboration/dialogues/2026-10-17-021-p4-live-ego-clock.md)。

## 修改

- 新增 EGO patch 0018：manager、FSM、规划可视化和 traj_server 均从所属 ROS node 读取仿真时钟，避免 spline 起始时间和轨迹采样／READY 使用不同 clock domain。
- `uav_navigation` 的 `/clock` 订阅使用 BEST_EFFORT 和独立互斥 callback group；保留已关闭 ROS context 时的 shutdown 防护。
- 更新 EGO patch/source manifest、接口契约、包说明、README、CURRENT、milestones、goal checklist，加入 P4 live integration 证据。

## 验证

- 固定 EGO revision 的 post-0017 文件上重放 patch 0018，五个改动 vendor 文件与当前构建源码逐字节匹配。
- ROS 2 Jazzy 新 build/install 目录构建 `uav_interfaces`, `traj_utils`, `uav_navigation`, `plan_env`, `path_searching`, `bspline_opt`, `ego_planner`，7/7 通过；事件日志 SHA-256 为 `3ce92cb5b22cf1508f7019029775ffced5fcbf5597525046b8186239e487fe19`。
- `python3 tools/test_navigation_task_state.py` 9项通过；`test_navigation_adapter.py` 与 `test_trajectory_server.py` 合成 ROS 测试通过。日志位于 `artifacts/runs/p4-navigation-live-ego-20261017-06/tests.log`。
- 动态 run #06 在 live D435i/VINS/plan_env 下生成目标 B-spline；请求 yaw 0.7 rad 被保留，spline 与第一条 READY stamp 相差7 ms；显式取消返回 `caller_cancel`，同 goal/epoch 的 ABORT 可见，ABORT 后 READY 数为0。
- `python3 tools/project_status.py`、`git diff --check` 和 `git diff --cached --check` 通过。

## 局限

- 同一6.13秒 map probe 的29组配对输入间隔 P95为0.396秒、最大0.495秒；该数据不证明地图更新稳定或达到任何已冻结阈值。
- 导航 supervisor teardown 日志有两条异步 Destroyable 异常；干净停机仍未验证。probe JSON 顶层 `latest_clock_ns` 为空，但嵌套 `trajectory_clock_check` 保存了3.969秒时钟值和 stamp 差，原始 run 报告保持不变。
- 没有轨迹 follower、PX4、SITL 控制或硬件；不证明实际跟踪、到达、避障、碰撞间距或取消后的飞行安全。P4及A–H均未通过。
