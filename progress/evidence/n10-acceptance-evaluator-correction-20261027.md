# N10.4 离线验收终态判断器修正

## 改动

- 新增 `tools/n10_terminal_readback.py`，将 bridge/PX4 终态、落地检测、终态后零控制、无旧 epoch goal/trajectory 与授权紧急 disarm 明确分开。字段缺失作为证据不足；读回状态或终态后行为不安全时显式失败。
- 更新 `tools/debug_truth/evaluate_n10_acceptance.py`：故障记录即使后续通过用户授权的 emergency disarm 到达 LANDED，也不能把这条原生故障处理判为 PASS；不完整或不安全的独立 readback 不能被 phase 字段单独覆盖。
- 更新只读 `tools/probe_px4_bridge_live.py`：捕获 PX4 command ACK、bridge/PX4/LandDetected 终态时间线、控制输出、给定 goal/epoch 后的旧目标与轨迹活动事件，以及终态持续时间和状态离开次数。
- 修复内容只改变归档证据采集/离线分类，不发布控制、不改变飞行准入、取消或降落行为。`config/acceptance.json` 的草案值及证据状态未因此升级。

## 证据

针对性及回归命令：

```bash
PYTHONPYCACHEPREFIX=/tmp/n10-pycache python3 -m py_compile \
  tools/n10_terminal_readback.py \
  tools/debug_truth/evaluate_n10_acceptance.py \
  tools/test_n10_terminal_readback.py \
  tools/test_n10_acceptance.py \
  tools/probe_px4_bridge_live.py
python3 -m unittest tools.test_n10_acceptance tools.test_n10_terminal_readback tools.test_n10_map_query_contract
```

结果：Python 编译通过，21 项测试通过。测试覆盖完整 native terminal、字段缺失、终态后控制、planner fault 无安全终态、以及 emergency disarm 不可替代 native fault landing。PX4 ACK 字段与当前生成的 `VehicleCommandAck.msg` 对照存在。

#391 离线结果仍为失败：goal dwell 单项可判定；full-body contact 和 native fault terminal 为 `FAIL`；map/resource 为 `INSUFFICIENT`。收尾补充与数值见[安全收尾和保持漂移复核](n10-integrated-calibration-closeout-and-divergence-20261027-391.md)。旧 run-local query response 缺少 radius 回显；修复只适用于后续采集，不倒改旧响应或使 #391 query 项通过。

## 限制与下一步

probe 已通过静态编译和字段审查，尚未在新的 live SITL 中验证其订阅与事件时间线输出。不得将紧急 disarm 分类为原生故障通过。后续需要实现修复、干净重建和一次代表性 live readback 之后才能关闭 N10.4；N10 仍 `in_progress`。
