# P4 导航 action 到达成功适配验证

- 任务：继续 GOAL.md P4，补齐 ROS `NavigateToPose` adapter 成功终态的合成集成验证。
- 用户约束：单 D435i 仿真范围；定位／目标使用匹配 epoch；不得将合成里程计或 P3 `debug_truth` 误报为真实闭环；保留既有用户改动并持续记录进度。
- 决策：新增独立 probe，不改动现有未跟踪的 `tools/test_navigation_adapter.py`。探针由合成 ROS peer 注入里程计，先令位置满足但 yaw 超容差，再令位置与 yaw 满足并持续 dwell；验证 action 成功与 EGO goal ID/epoch 一致。
- 结果：固定 Jazzy 镜像内运行通过，action 返回 `SUCCEEDED/position_yaw_tolerance_held`；probe 中断条件确认 yaw 不满足时 action 未提前成功。加载的导航模块 SHA 与当前生产源码相同。
- 限制／待办：此测试不执行 EGO B-spline、不跟踪真实机体位姿、不验证 PX4、障碍或完整 P4。仍需真实轨迹控制/到达、故障响应、多地图场景和长时运行。
- 证据：`progress/evidence/p4-navigation-action-success-adapter.json`；原始 probe 输出 `artifacts/runs/p4-navigation-action-success-20261017-85/arrival-probe.json`。
