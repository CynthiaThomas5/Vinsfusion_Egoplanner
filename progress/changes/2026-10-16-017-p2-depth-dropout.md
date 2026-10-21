# P2 深度断流源时间注入

- 对话摘要：[P2 深度断流注入](../../collaboration/dialogues/2026-10-16-017-p2-depth-dropout.md)
- 文件变化：`tools/fault_relay.py` 新增 `depth` 路由；`tools/test_fault_relay.py` 验证映射和源时间窗口；VINS 调试说明、README、CURRENT、P2 里程碑与 E 清单加入注入范围和限制；新增 P2 轻量证据报告。未改地图或控制源码。
- 验证命令：`docker exec d435i-vins-build bash -lc 'source /opt/ros/jazzy/setup.bash; cd /workspace; python3 tools/test_fault_relay.py'`，2 项测试通过。
- 运行：派生 Jazzy 镜像 `sha256:fbdf66eb12efdea888acdafeb501280fa108513ae6b7703fe2a699ba97989f8e`。使用 `/clock` 与 D435i 深度帧录包，随后在 ROS domain 98、99 中分别启动新 relay 与 bag player，注入窗口按首个深度 header stamp 后 3–8 秒设置。
- 结果：两次 `window_observed=true`。第一次收到1034帧，窗口内丢弃51帧，窗口后恢复957帧；第二次收到984帧，丢弃47帧，恢复904帧。完整计数、stamp 和 artifact 哈希见[证据报告](../evidence/p2-depth-dropout.json)。
- 采集问题：预期6秒结束的录包因后台任务忽略 SIGINT，持续约160秒；日志报告2344条传输丢失。该 bag 仅作为此次故障注入输入，不作为频率或数据完整性结论；第一次 setup 失败和修正后的采集日志均保留。
- 局限：没有地图运行节点消费恢复前后的深度，因此本次没有检测 stale depth、冻结/清空旧地图、规划保护或 PX4 状态响应。E 条件仍未满足，不能据此宣称安全门控通过。
- 下一步：先实现并验证地图对深度过期的 fail-closed 行为，再将同样断流注入接到地图状态和消费者输出上；保持 PX4 控制出口断开。
