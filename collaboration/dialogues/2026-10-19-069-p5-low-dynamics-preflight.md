# P5 低动态 EGO 配置与 PX4 preflight 诊断（#188–#190）

为了验证较缓和轨迹是否能降低视觉跟踪压力，新增项目内的 `ego_planner_slow_probe.json`，值为0.25 m/s与0.4 m/s²；默认 EGO 配置不变。闭环 launch 现在允许通过 `planner_config:=<project-relative-json>` 选择参数源，检查路径必须位于项目根目录内，并将实际路径与 SHA-256 写入 VINS session manifest。

#188 在起飞前因优化里程计／telemetry 年龄0.304秒超过既有0.300秒上限而锁定；#189 的定位和建图前置条件通过，但PX4 preflight检查全程为false，报告 `ekf2 missing data` 和 `system power unavailable`，桥未解锁且未发 goal。#190 使用 run-local action 探针要求 `pre_flight_checks_pass` 为真后才调用 enable；等待60秒仍未通过，所以没有 enable 请求、解锁或 goal。三轮低动态配置虽由 manifest 确认加载，但均未执行目标轨迹，不能判断低动态是否改善质量代价。

6项参数／manifest测试、`uav_px4_bridge` Jazzy隔离构建1/1、launch参数探针和结构检查通过。健康阈值、PX4参数及默认规划器没有改动。证据和哈希见 [P5 低动态与 preflight 诊断 #188–#190](../../progress/evidence/p5-vio-low-dynamics-preflight-20261019-188-190.json)。P5仍进行中；下一步先使启动 freshness 和PX4 preflight可重复，再重试低动态目标。
