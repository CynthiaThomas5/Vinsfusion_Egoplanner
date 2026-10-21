# P5 bridge 时间戳回退修复与独立复测

关联对话：[bridge 时间戳回退诊断](../../collaboration/dialogues/2026-10-19-067-p5-bridge-timestamp-fallback.md)。

## 修改

- `px4_bridge_node.py` 在 lockstep 时间映射失败、但 timesync 新鲜时，用当前系统／Agent 时间作为 PX4 控制消息时间戳。旧实现复用 `TimesyncStatus.timestamp`，该字段代表样本时间而非当前时间。timesync 不新鲜仍 fail closed。
- `time_mapping.py` 增加可独立测试的回退规则；映射测试覆盖新鲜与不新鲜两种情况及非正时间。
- #182 ULog 与探针时间线对应到一次5.557秒回退；经 PX4 offset 换算后旧1.024秒，和 `COM_OF_LOSS_T=1.0` 一致。

## 验证

- `python3 tools/test_px4_bridge_time_mapping.py`：16项通过；bridge control 11项、frame 19项、VIO profile 7项通过；`py_compile` 通过。
- 隔离 Jazzy colcon 构建 `uav_px4_bridge`：1/1包通过；#183 launch 运行时 package prefix 确认为 run-local overlay。
- #183 记录236条轨迹设定点，时间戳无回退、间隔48.890–51.034 ms；没有完成悬停。约15.19秒 localization 变为 `telemetry_stale`，bridge 看到 odometry receipt 年龄0.3719秒，按既有0.3秒门限降落。最终 landed/disarmed，真值只读 observer 完成90秒采集。

## 局限与下一步

#183没有记录 mapper fallback 分支计数，单靠 setpoint 单调不能证明该分支在本轮被实际触发；回退函数由定向单测覆盖。该次主中止为定位／odometry 新鲜度，不是悬停基线。下一步对齐 VINS telemetry、优化里程计、定位状态和 `/clock` 年龄，保留0.3秒门限及其他安全门。P5仍未通过。

详细输入、状态时间线和工件 SHA-256 见 [`p5-vio-hover-timestamp-fallback-20261019-183.json`](../../progress/evidence/p5-vio-hover-timestamp-fallback-20261019-183.json)。
