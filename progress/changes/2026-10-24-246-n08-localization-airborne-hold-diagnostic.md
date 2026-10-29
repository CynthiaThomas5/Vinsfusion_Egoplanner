# #246 N08 定位新鲜度与低速曲线诊断

关联对话摘要：[2026-10-24-246](../../collaboration/dialogues/2026-10-24-246-n08-localization-airborne-hold-diagnostic.md)。

## 修改

- `src/own/uav_localization/uav_localization/health.py`：Health 锁存快照加入首次 stale 观测的 stream、源龄/接收龄、门限与当前时钟戳。
- `src/own/uav_localization/uav_localization/node.py`：健康已锁定后仅记录第一条到达的 telemetry 诊断字段。
- `tools/test_localization_health.py`：增加 stale 快照字段测试。
- 未改健康行为、阈值、PX4 时间算法或 N08 速度／地图验收门。

## 验证

- `python3 -m unittest tools.test_localization_health`：14 项通过。
- `bash tools/project.sh build ros`：17 个 ROS 包构建完成。
- #246 same-profile fresh SITL：HRT／ROS 266/266 有效，LocalizationStatus 304/304 有效；未复现 #245 telemetry-stale。
- compute-only evaluator 12/12；曲线证书因 x 轴单轴速度上界与起点 hold unknown 拒绝，未执行 XY。
- 结束前确认 landed/at-rest、DISARMED、bridge control disabled、fixture absent；容器退出码 0。

## 限制与后续

#245 的 telemetry-stale 调度根因未证实；不得称为修复。#246 没有制动量测，也不能通过 N08。下一子项 #247 用当前地图的负 Y unknown 薄带作为新证据，只改变观察方向，保持原证书阈值。
