# P4 ROS action 到达成功适配验证

对话摘要：[2026-10-17-043](../../collaboration/dialogues/2026-10-17-043-p4-navigation-action-arrival-adapter.md)。

## 改动

- 新增 `tools/probe_navigation_arrival_adapter.py`：在独立合成 ROS peer 下调用 `NavigateToPose`，注入当前 epoch 的新鲜里程计，验证位置和 yaw 两个条件共同满足并持续 dwell 后返回成功。位置符合但 yaw 不符合时，验证 action 不会提前成功。
- 新增运行原始结果、输入清单及轻量报告：`artifacts/runs/p4-navigation-action-success-20261017-85/`、`progress/evidence/p4-navigation-action-success-adapter.json`。
- 更新 `progress/CURRENT.md` 和 P4 里程碑证据列表。没有更改导航生产节点；P4 仍为 `in_progress`。

## 验证

- `python3 -m py_compile tools/probe_navigation_arrival_adapter.py`：通过。
- `python3 tools/test_navigation_task_state.py`：10 项通过。
- Jazzy 固定镜像中运行 probe：`PASS_ACTION_ARRIVAL_SUCCESS`；action result 为 `success=true, reason=position_yaw_tolerance_held`。运行加载模块 SHA `0c2789a1d434ce302d5a3716119a8d54b902a90a0d4c34507eeb79b1c678d9c9` 与当前 `node.py` 一致。
- `python3 tools/project_status.py`：结构检查通过，仅说明结构一致。
- `git diff --check`：通过。

## 局限与下一步

Probe 通过合成里程计验证 ROS action adapter 的终态映射；它不是机体运动，也不能证明 EGO 样条跟踪、闭环到达、障碍净空、PX4 或 GOAL D/E。下一步仍要完成实际控制轨迹的跟踪／到达，随后覆盖地图与定位故障、多场景地图快照和连续负载运行。

主要证据：`progress/evidence/p4-navigation-action-success-adapter.json`。
