# N08 #245 定向低速配置与 freshness 失败定位

## 实际改动

- 归档 #245 同 run PX4 时钟／定位 source timeline、compute-only 拒绝与落地读回。
- 更新当前状态并登记下一子任务 #246。未改健康阈值、N08 出口或 N07 累计通过状态。

## 验证

- `docker exec ... ros2 topic echo --once ...`：PX4 DISARMED、landed/at-rest、bridge DISABLED/control disabled；LocalizationStatus `telemetry_stale`。
- `gz model --list` 过滤读回仅见 `x500_d435i_0`，未见 fixture。
- `bash tools/project.sh stop n08-20261024-245-low-speed-vector-cap`：exit 0；`docker inspect`：容器 `exited`, exit 0。
- source timeline：PX4 time-domain 423/423 有效，HRT/ROS gap −0.128…+0.012 s，0 回退；adapter freshness 在约 1.507 s 锁存，telemetry/optimized 源龄 0.372 s > 0.300 s；raw observer 后续持续收到 VINS。
- 本轮只归档与更新文档；未改代码，因此没有新增构建或回归测试。

## 限制与下一步

这证明本轮不是 PX4 时钟对齐导致的拒绝；但尚未解释 adapter 为什么未在锁存前接受推进中的 raw VINS sample。N08 仍不能进入实际低速移动／制动测量。下一项对齐 observer、adapter callback、`/clock` 与 QoS/executor 时序，再决定最小修复；不放宽 freshness 门。
