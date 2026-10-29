# N08 #323 初始 N05 前的 VINS telemetry freshness lockout

运行证据：[报告](../evidence/n08-terminal-stop-20261026-323-telemetry-lockout.md)、[JSON](../evidence/n08-terminal-stop-20261026-323-telemetry-lockout.json)。对话摘要：[2026-10-26-323](../../collaboration/dialogues/2026-10-26-323-n08-telemetry-lockout.md)。

- 初始 N05 snapshot checker 在150秒内收到 localization/map/bridge/clock，但缺少 /localization/optimized_imu_odom，因此 fail-closed。没有fixture、goal、control enable或flight。
- 原始 localization_adapter 日志确认 sim t=9.78s telemetry source-age=0.340s，超过保留的0.300s门限；receipt-age=0.308s仍在0.500s以内。normalized cost=0.08980，solver状态有效。health lockout 后持续 LOST/telemetry_stale；后续VINS原始流恢复不自动清除锁存。
- independent readback确认 fixture未spawn、bridge DISABLED、PX4 disarmed/landed、控制topic计数0；只停止本run容器，exit0。
- 该 run 不计普通terminal_stop次数，N08仍in_progress；不修改任何freshness阈值。下一项#324以同一冻结版本做全新独立冷启动，针对新的PX4/VINS epoch判定startup telemetry gap是否重现。
