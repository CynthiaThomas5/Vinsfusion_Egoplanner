# P5 VIO–PX4–EGO 配置与质量门复核（#160–#171）

## 范围与约束

继续 `GOAL.md` 的单 D435i、无真值 VIO 闭环。P0–P3 状态不变；P4/P5 继续推进，P6 与 GOAL A–H 未完成。SITL 诊断不替代长时、地图/避障或最终验收；PX4 控制只由 `uav_px4_bridge` 发布，最终 VIO 运行图不得订阅 debug_truth 或完整世界地图。

## 本轮决定

- #168 完整 EGO 参数 run 观察到 PX4 attitude source age 最大提前 `/clock` 53.930 ms，超过原 VIO profile 50 ms future 容差并触发安全降落。因此只将 `config/components/px4_bridge/vio_closed_loop.json` 的 VIO 专用 `px4_source_timestamp_max_future_sim_s` 提至 65 ms。共享与 `debug_truth` profile、stale/receipt 年龄及定位质量门未变。该容差仍是 PROVISIONAL；#170/#171 提供两次后续复核，仍不足以冻结该容差。
- `max_normalized_cost=1.0` 保持不变。#170 在无真值图中通过前置稳定门、进入 ACTIVE 并发送目标，但 normalized cost 达 1.159354 后 action fail-closed，飞控随后安全落地解除武装。尚无独立位姿误差证据可据以校准质量阈值。
- #160/#163/#166 的 run-only EGO launch 未传完整项目参数与模型内参，只作诊断。#168/#170 已传 `ego_planner.json`、`ego_input.json` 参数与由 D435i SDF 导出的内参；并新增 canonical `vio_closed_loop_ego_px4.launch.py`：从项目 configs/SDF 解析参数、创建不可复用 session，并启动完整 no-truth ROS 侧链路。

## 证据与待办

轻量验收报告 `progress/evidence/p5-vio-ego-closed-loop-20261019-160-171.json` 记录 #160–#171 的排除/失败分类、相关 artifacts 哈希、#170 定位质量与新鲜度样本、truth graph 与控制发布者检查。#161 因 DDS domain/端口映射排除；#162/#164 定位前置门未开；#165 PX4 遥测年龄超限 1 ns；#167 goal JSON 格式错误；#169 Colcon build 目录错误；均未发送目标。#168 的 50 ms future limit 失败后，#170 在 65 ms 下未再因 future-age 触发降落，但仍因质量门中止。#171 使用 canonical launch、启动 VINS/EGO/PX4 闭环并派发目标，随后在 normalized_cost=1.011447 处中止，安全落地解除武装。

固定 Jazzy 新目录14包构建通过，ROS launch 参数解析及隔离启动/清理 smoke 通过。#171 首次真实 SITL 使用 canonical launch：稳定门、ACTIVE 和 goal dispatch 均通过；normalized_cost=1.011447 触发既有门控，PX4 landed/disarmed，状态末值 failsafe=false。四个 PX4 控制输入 topic 各一个发布者，bridge 图无 debug_truth 输入。P5 未通过。下一步将 quality/特征、运动和只读误差评估对齐，不调低1.0门限，再复跑目标与障碍场景。
