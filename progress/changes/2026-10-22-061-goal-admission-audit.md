# #061 离线目标准入审查

对应[对话摘要](../../collaboration/dialogues/2026-10-22-061-goal-admission-audit.md)，[完整证据](../evidence/goal-admission-20261022-061.md)。没有新飞行或阶段升级。

- 新增`tools/debug_truth/world_geometry.py`：共享有符号box／cylinder距离、平面pose组合、受限静态SDF解析和带半采样间距余量的连续直线下界。
- 新增`tools/debug_truth/audit_navigation_goals.py`：以保存世界哈希和原始单一起飞前对齐审计目标球、非地面固定XY列和直线连接；候选只输出离线报告，flight_admissible始终false。
- `tools/debug_truth/evaluate_clearance.py`改用共享基础距离函数；三个真实run的完整结果JSON回归一致。源记录未改。
- 新增`tools/test_goal_geometry_audit.py`七项边界测试，包括薄障碍位于采样点之间仍拒绝、不支持的世界结构拒绝和空几何失败；非法目标偏移CLI负例拒绝并无输出。
- docs／navigation README澄清目标接受不等于地图／机体空间准入，旧配置保持禁用。未修改在线算法或健康／控制参数。

验证：两份#060真实数据离线复算；175项全回归＋真实ROS action／250Hz时钟测试通过；Python编译、project_status和git diff --check通过。无ROS源码／binary变更，无需新ROS编译；未启动SITL或实机。项目仿真保持关闭，未提交／推送。

确认：目标入口缺少空间查询，unknown与inflation mask独立，部分碰撞检查只覆盖前2/3；但缺少目标时刻原始体素快照，不能给旧目标的在线地图状态或具体净空失败因果链定论。13m偏移候选的端点／16→13直线标称非地面余量较大，但不是在线路径或飞行安全通过；下一步先做只读目标准入查询的隔离验证。
