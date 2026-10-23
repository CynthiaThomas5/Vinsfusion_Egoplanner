# #077：074-02回环yaw权重离线重放

[批准范围与预先判定标准](../../collaboration/dialogues/2026-10-22-077-loop-yaw-weight-replay.md)。增加了独立离线重放器[`replay_loop_yaw_graph.py`](../../tools/debug_truth/replay_loop_yaw_graph.py)及其Ceres残差实现[`loop_graph_ceres_replay.cc`](../../tools/debug_truth/loop_graph_ceres_replay.cc)。它按固定Ceres 2.2环境复建074-02保存的四次4DoF图优化；Ceres只接收VIO关键帧和PnP回环边，真值仅在求解后用于误差评分。工作区以只读方式挂载，容器断网；未启动仿真。

## 验证

- `PYTHONPYCACHEPREFIX=/tmp/codex-python-cache-077 python3 -m py_compile tools/debug_truth/replay_loop_yaw_graph.py`：通过。
- `docker run --rm --network none -v /home/huangxiaocheng/D435i-VINS-EGO-ROS2:/workspace:ro -v /tmp/codex-loop-yaw-replay-077:/out:rw -w /workspace d435i-vins:dev bash -lc 'source /opt/ros/jazzy/setup.bash; python3 tools/debug_truth/replay_loop_yaw_graph.py --run-dir artifacts/runs/real-loop-20261022-074-02 --output /out/loop-yaw-weight-replay-20261022-077.json --markdown /out/loop-yaw-weight-replay-20261022-077.md'`：退出0，基线复现和A/B计算完成。实际镜像ID匹配`config/runtime.json`锁定值。
- 基线0.1重放中，四次图快照关键帧最大位置差约`1.1e-16 m`、全姿态差`1.21e-6°`；四个raw→corrected输出变换通过门限；4,586对轨迹逐样本最大位置误差差`6.8e-16 m`、yaw误差差`2.9e-14°`；七次返航末10秒的RMSE也均在预设门限内。
- 只把yaw残差缩放改为1.0后，四条最终回环平均绝对yaw残差由`0.7959°`降到`0.2250°`（71.7%）；第7次返航末10秒yaw RMSE由`1.2869°`降至`0.6114°`（52.5%）。同期位置RMSE由`4.915cm`升至`5.929cm`（回归20.6%，超过预设5%上限）；但仍比原始VINS的`12.348cm`低52.0%。因此低yaw权重确实限制了此图的航向修正，单独提高权重却未通过联合接受标准。
- 同一Huber(0.1)作用于4维回环残差块。按最终残差和Huber导数计算，四边平均平方根权重从`0.9717`降到`0.7479`，数值上支持“增强yaw项会连带降权平移项”的可能机制；这不是独立干预证据，不能断言它造成了位置回归。
- 原独立回环评估13项检查、无真值输入检查和依赖锁定的三个运行源码哈希均通过；输入哈希与#076核验一致。

机器结果及完整逐边数据见[证据报告](../evidence/loop-yaw-weight-replay-20261022-077.md)和[JSON](../evidence/loop-yaw-weight-replay-20261022-077.json)。本次只新增离线分析工具和记录，没有改生产源码、参数、健康门、导航或控制链路；没有构建自维护ROS包或SITL，因为目标是隔离的固定数据Ceres回放。正式里程碑不变。

## 限制与下一步

这是一个已存档回环图上的确定性干预，不证明新会话的回环几何准确度或重复性。缩放1.0不进入默认参数。下一候选目标是离线验证回环yaw与平移使用独立Huber残差块后，能否保留yaw改善并避免位置回归；需用户另行批准。
