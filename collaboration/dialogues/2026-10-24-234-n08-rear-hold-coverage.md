# N08.2x #234 任务摘要

- #233 同身份 raw map 的 start hold 有 394 个 unknown，全部在起点相对 ENU −X 后向薄层；goal hold 有 472 个 unknown。compute-only 在 B-spline 前拒绝。
- #234 保留相同 overhead/ground scan、目标、场景与门限；只将 N05 yaw 扫描从已验证的 −π/2 延长到 −π、pitch 0，再分段经 −π/2、0 回中。
- 先 DISARMED N05 scan；只有 profile 完成、fresh post-release/current-area admission 通过才运行同一 compute-only。无 XY，无制动测量。

- #234 结果：19/19 stages 完成；N05 after/post-release online/offline 同身份一致拒绝 TAKEOFF_CONTACT 的 33 个 above-ground unknown。HOLD 0 unknown。未启动 compute-only，无 XY；最终 landed/DISARMED，fixture absent，container exit 0。
- #235 唯一变化：在 yaw=−π 添加 pitch=+0.45 rad 下视阶段后回到 pitch=0；其余路径和门限冻结。只在 fresh post-release/current-area N05 准入通过后进入 compute-only。
