# #213 N08 compute-only 目标准入拒绝

- 运行：新冷启动 `n08-20261024-213-compute-01`，先完成全机支撑观测，再在 fresh N05 current-area online/offline gate 通过后运行 compute-only。
- 结果：launch 图确认 bridge 只订阅隔离话题；目标 action 请求被接受，但 `NavigationCommand` observer 收到 0 条消息、EGO 没有 READY PositionCommand。runner 报 `ego_ready_trajectory_not_observed`，超时后 bridge `operator_disable`，确认落地解除武装并停止容器。无 EGO 轨迹、无平移或制动数据。
- 诊断：按 frozen raw occupancy snapshot 与 `0037-readonly-sphere-query.patch` 的闭球相交规则复算 +Y 0.6 m 目标，2,181 个相交体素中 333 unknown、0 occupied。快照早于起飞数十秒，所以“目标 admission 因 unknown 拒绝”是强推断，不是 action-time service 响应。附近离线扫描找到一个全 free 球候选 `-Y 0.4 m`，仅供下一轮 compute-only 实时复核。
- 验证：readiness 与 N05 current-area gate 接受且 online/offline 一致；运行期 ROS 图查询确认 `/position_cmd` 订阅数为 0，隔离话题唯一订阅者是 bridge；`tools/project.sh stop n08-20261024-213-compute-01` 正常停止。
- 局限：支撑扫描器自身因未及时读到 fresh DISARMED 回执返回失败；夹具模型 absent、attachment detached、最终 landed=true，但回执年龄 4.07 s。wrapper 保留容器供监护；随后 fresh read-only gates 通过才启动无平移的 compute-only。
- 证据：[运行拒绝报告](../evidence/n08-compute-only-refusal-20261024-213.md)与 [JSON/hash 记录](../evidence/n08-compute-only-refusal-20261024-213.json)。
- 下一步：让 runner 保存 action terminal reason、失败时先取消任务并记录最终桥接状态；使用新冷启动对 -Y 0.4 m 候选重新验证。未知拒绝、半径与停止边界均不放宽。
- 对话摘要：[N08.2c #213](../../collaboration/dialogues/2026-10-24-213-n08-compute-only-refusal.md)
