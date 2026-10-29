# #463 N10.6 重建后回归

- 在用户授权的 N10 Goal 范围内，用 #462 clean install 执行 N10.6 回归。596 项测试及导航适配器/官方 EGO 策略探针通过。
- 代表性 PX4 任务在目标提交前被 `n09_runtime.sh` 的 `/navigation/ego_goal` subscriber 计数断言拒绝。实际 graph 有 supervisor publisher，以及 `drone_0_ego_planner_node` 和 `uav_px4_bridge` 两个接收端；N10 冻结契约同样记为两个接收端。
- PX4 在拒绝后仍 disarmed/landed，bridge disabled、无 goal；受控 stop 成功，未使用紧急 disarm。
- 已更正 N09 与 N10 cancel wrapper 的图计数/接收端检查。由于 shell runner 纳入运行身份，需重新做 N10.5 干净重建；修复后的 N10.6 完整任务仍未完成。
- #434 排除故障注入及故障后校准保持有效，N15/N16 正式次数不因这轮测试获计数。
