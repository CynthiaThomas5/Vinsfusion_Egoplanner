# N08 #323 初始 N05 前 telemetry freshness lockout

- N08 Goal completion mode 继续；保持所有 health/time/map/speed/tracking threshold 不变，N07不复测。
- N05 初始在线检查150秒未收到 optimized_imu_odom，缺失 odom，未到 fixture/mission/goal/enable。
- 源码日志的 health_lockout_snapshot 将原因定位到 sim t=9.78s telemetry source-age=0.340s > 原门限0.300s；receipt-age0.308s < 0.500s，normalized cost0.0898。后续原始VINS流回升，但 adapter 按原设计锁存 LOST。
- 独立读回确认无 fixture、bridge DISABLED、PX4 disarmed/landed、控制消息0；项目容器 exit0。
- run #323 留作前置拒绝，不计三次普通到达。继续#324使用完全相同冻结版本/new PX4-VINS epoch，阈值不动。
