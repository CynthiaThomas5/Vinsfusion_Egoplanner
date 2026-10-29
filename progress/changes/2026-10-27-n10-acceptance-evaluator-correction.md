# N10.4 终态读回与故障分类修正

对话摘要：[离线终态判断、采集器和不新增运行门的约束](../../collaboration/dialogues/2026-10-27-n10-acceptance-evaluator-correction.md)。

新增只读 `tools/n10_terminal_readback.py`，并更新 `tools/debug_truth/evaluate_n10_acceptance.py`，使终态证据必须同时覆盖 bridge/PX4 landed/disarmed、控制关闭、终态后无控制、无旧 epoch 目标/轨迹。缺字段保留为不足；可见不安全状态显式失败；授权 emergency-disarm closeout 永远不能被记成原生 fault landing 通过。`tools/probe_px4_bridge_live.py` 增加 ACK、桥/PX4/land detector 状态、控制消息及指定 goal/epoch 之后的旧目标/轨迹 readback。

验证：上述 Python 文件编译；`python3 -m unittest tools.test_n10_acceptance tools.test_n10_terminal_readback tools.test_n10_map_query_contract` 共 21 项通过。字段名与当前 `VehicleCommandAck.msg` 对照。probe 尚未在修复后 SITL 上做实时验证；没有改变 `config/acceptance.json` 阈值或运行控制行为。具体分类结论见[验收判断器证据](../evidence/n10-acceptance-evaluator-correction-20261027.md)。

N10.4 仍未完成：需要当前有效配置身份绑定、完整校准数据和重建后 live readback；不把静态编译/单测当作运行通过。
