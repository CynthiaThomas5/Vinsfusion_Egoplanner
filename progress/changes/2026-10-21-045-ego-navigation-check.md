# 当前 ego 房间导航链验证

对应[对话](../../collaboration/dialogues/2026-10-21-045-ego-navigation-check.md)及[证据](../evidence/ego-navigation-check-20261021-01.json)。

文件：本记录、对话、证据与 CURRENT；探针和原始报告位于 `artifacts/runs/ego-navigation-check-20261021-01`。未修改产品源码、地图参数、健康或时效阈值。

输入与边界：同一运行容器和 epoch，在定位 TRACKING、地图 ready（525占据点）时发当前 odom X 前方0.8 m、等高目标。桥 DISABLED、ready=false、external_odometry_stale，未使能／解锁飞行。探针只订阅状态与轨迹，使用正式 `/navigation/navigate_to_pose` action；没有发布 PX4 控制或真值。

结果：action 接受，目标 ID `436f3e8f2fb64198a3104fa222a7e831`；收到1条同 goal_id/epoch 的 B-spline，9个控制点全部有限；轨迹服务器发19条匹配 READY 指令。随后 action ABORTED，reason=pose_stale，traj_server abort，EGO取消对应目标和轨迹。所有采到的桥状态均未解锁且control_enabled=false。未到达目标，因此不能称导航成功。

原因与限制：日志显示优化 odom 回调间隔多次约0.35–0.43墙钟秒，超过 `task_supervisor.json` 的0.3秒门。桥也报里程计过期。具体调度／RTF根因尚未由此测试隔离。地面等高目标仅验证规划接口，不证明起点机体净空、路径可飞、终点到达、绕障或连续导航。首轮探针 float64 字段使用整数导致转换失败，修正为12.0后重跑，先前失败不计产品失败。

验证命令：容器同ROS domain214加载已有全栈overlay与当前6包install运行 `probe.py`；回读JSON断言目标身份、样条数、19条READY、pose_stale终态、有限控制点与全窗bridge未解锁均通过。`python3 tools/project_status.py`、`git diff --check`通过。无需重新构建ROS包。阶段不升级。

下一步：保持现有阈值，先对比关闭GUI与当前GUI负载下的RTF、优化odom接收间隔和桥ready持续时间，解决数据时效后再做无目标悬停及EGO目标执行；飞行前仍需地图unknown、起点和完整机体净空验证。仿真继续运行，目标已自动取消。
