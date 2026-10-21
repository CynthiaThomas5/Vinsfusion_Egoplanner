# EGO 导航验证

用户要求：验证当前能否进行 EGO Planner 导航。

本轮先检查飞行前置条件，再测试导航 action、EGO 样条及轨迹输出。飞控桥 ready=false、external_odometry_stale，因此仅在桥 DISABLED、未解锁下发规划目标，不调用 Offboard enable 或执行飞行。不改健康和时效阈值。结果以运行证据为准。
