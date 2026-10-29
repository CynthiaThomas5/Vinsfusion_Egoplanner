# 2026-10-27 N10.3/#401 故障路径校准归档

## 本轮改动
- 新增 planner-process-exit 当前版本校准报告，记录 fault trigger、匹配 identity、action ABORTED、PX4/bridge 安全终态、零控制、接触结果和传感器归档完整性。
- 将 #401 限定为单类 calibration PASS；不计 N15 正式次数，不宣称导航任务成功或整个 N10 通过。
- 紧急 disarm 未使用；其一次性授权此前已在 #391 收尾中使用。

## 验证
- 读取 #401 原始 injection、flight、终态 readback、safe-to-stop、contact 和 capture artifacts；关键 SHA256 收录于 evidence JSON。
- Fault path build/regression identity is referenced from #392 report: 17 ROS packages and 471 tests passed before the frozen runtime run.
- No code change to the navigation safety path in this archive-only step.

## 限制与下一步
- 只验证 planner process exit 类别一次。其他断流、epoch/restart、clock rollback 故障类别仍按复用矩阵补证。
- 下一项记录方法准备 #402；随后 #403 处理采样间净空界，再安排综合校准。
