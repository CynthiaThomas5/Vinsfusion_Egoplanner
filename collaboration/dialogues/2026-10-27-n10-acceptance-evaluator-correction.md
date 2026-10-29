# N10.4 离线终态判断修正摘要

## 决定

- 将完整 PX4/bridge 终态、终态后零控制和无旧 epoch 目标/轨迹作为离线故障结论所需证据。
- emergency disarm 只分类为会话安全收尾，不满足 planner fault 原生降落出口。
- CPU、记录器、统计量不接入起飞拒绝、取消或降落控制；缺失数据按不足处理。
- 保留当前验收草案数值与原始运行证据，不把测试或补录改写为飞行通过。

## 产物与状态

实现文件为 `tools/n10_terminal_readback.py`、`tools/debug_truth/evaluate_n10_acceptance.py` 和 `tools/probe_px4_bridge_live.py`，回归见 `tools/test_n10_terminal_readback.py`、`tools/test_n10_acceptance.py`。21 项定向测试和 Python 编译通过；probe 的实时输出尚待修复后 SITL 核验。N10.4 仍 `in_progress`。
