# N10.3/#368：扩大 PX4 仿真时钟映射历史窗口

关联对话：[诊断决策](../../collaboration/dialogues/2026-10-27-367-n10-clock-history-block.md)。协议：[冻结协议](../evidence/n10-live-obstacle-clock-history-replan-protocol-20261027-368.md)。

## 根因和唯一变量

#367 的 bridge 在sim 129.264s拒绝一条时间戳128.968s的VIO样本，报`source_stamp_outside_clock_history`；0.296s仿真延迟对应约0.345s墙钟龄，低于现有0.35s源龄上限。当前64个`/clock`样本只覆盖约0.256s仿真历史，所以短样本缓存先于龄门限阻挡了正确插值。

仅将`config/components/px4_bridge/debug_truth.json`中的`clock_mapping_max_samples`从64改为128。保留0.35s映射源龄、0.3s映射后里程计接收龄、0.5s ROS clock stale、source timestamp range和PX4桥其他控制/融合/定位约束。

## 验证

- `python3 tools/test_px4_bridge_time_mapping.py`：23项通过。新增测试证明旧64样本窗口拒绝0.296s合法延迟，新128样本配置正确插值并仍拒绝超过0.35s源龄的样本。
- `bash -n`及4个run-local Python工具编译通过；`git diff --check`通过。
- 该修改只涉及运行时JSON参数和测试，不改编译源码，因此不重建ROS包；SITL会从当前唯一配置加载新窗口。
- 候选runtime contract：`68aba197b9db4e6a405baaaafccdcec91ba91434e3525f56b701f9c5a6772734`（665项）。

## 下一步

#368复跑同一单箱PX4 SITL。run尚未启动；工具、协议哈希与runtime身份已冻结。#367仍保留为目标失败，不能用该参数变化覆盖其记录。
