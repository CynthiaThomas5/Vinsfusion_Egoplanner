# N07 #191：N05 通过后 PX4 时间龄门触发安全降落

**结果：N07 evaluator FAIL；连续合格冷启动仍为 0/3。** Run：`artifacts/runs/n07-20261024-191-01/`。完整量测和 SHA-256 索引见[JSON 报告](n07-px4-telemetry-stale-20261024-191.json)。

## 固定条件与 N05

image、runtime contract、spawn `-6.5,0,0.3,0,0,0`、wall layout、`n06_full_airframe_retreat_240_oblique_separated_return`、N05/health 阈值以及 30 秒 no-goal hover 与 #190 相同。初始门按预期拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`；支架标记 12/12 阶段、同一 epoch/map、attached、DISARMED、无真值/控制。Attached、post-release、current-area 的 online/offline 检查全部 accepted，N05 summary 14/14。

Fixture helper 记录 `fresh DISARMED status is required for every fixture command` 后退出 1，但记录 12/12 阶段、attached→detached、fixture removed/scene absent、PX4 `vehicle_states=[1]` 且最终 landed；最终 localization valid、normalized cost 0.452。失败字段保留，释放后和 current-area gate 仍按在线/离线及 identity 单独判定通过。

## Hover 中止与定位时间线

no-goal 前置满足并使桥 enable；没有 navigation goal 或 PositionCommand。飞行桥进入 ACTIVE/armed 后仅保持 2.64 仿真秒，随后因 `px4_telemetry_stale` 触发 `SAFETY_ABORT`，桥进入 LANDING 并自动降落，disable 接受，最终 landed/disarmed。PX4 ULog 分析 12/12 全通过，包括 EV position/yaw 实际融合、无 GNSS aiding、最终 landed/disarmed。独立真值和估计误差记录完整，但短暂保持不满足 30 秒出口。

在桥首次报告 `px4_telemetry_stale` 的样本，PX4 local-position 与 attitude 的回调 receipt age 仍很小，但其时间戳相对于映射后的仿真时钟分别约超前 144 ms 和 136 ms；`px4_source_timestamp_max_future_sim_s` 为 65 ms，二者均越过该 fail-closed 允许范围。bridge 状态显示 time-domain validity 仍 true。随后 LocalizationStatus 锁存 `telemetry_stale`；bridge 当时已进入 LANDING。该证据说明直接触发的门是 PX4 源时间戳 future-age 检查；时钟映射、PX4 源时刻或负载调度中的哪一项造成这次偏差尚未区分，不能据此调整 65 ms 门限。

## Graph 与严格评估

run-local 只读等待器观测到 bridge `ACTIVE && armed` 后才启动原 `capture_n07_ros_graph.py`。由于 bridge 在 2.64 仿真秒后安全降落，graph recorder 未采到 airborne snapshot：pre-enable-labelled snapshot 中控制 topic publisher 数为 0，结束 landed snapshot 每个 topic 都只有一个 `uav_px4_bridge` publisher，且两个快照均无 truth ROS 名称。原 evaluator 仅 hover 时长和 graph unique-owner 两项失败，其余融合、健康窗口、时间映射、独立误差与安全落地检查通过；结果仍是 FAIL，不计入三连。

`bash tools/project.sh stop n07-20261024-191-01` 后容器 `exited 0`，无活动项目容器。运行没有继续起飞或重试。

## 下一步

N07.38 #192 保持所有控制、runtime、N05 和健康门限不变，只去掉 N07 非必需的 full-window freshness probe；flight 的定位健康 history 与必需 truth/alignment/bridge 记录器继续覆盖实际 hover，graph ACTIVE 窗口记录方式保持 #191。假设是额外 probe 的订阅/处理负载可能促进 PX4 源时刻与映射仿真时钟的暂时偏差；通过同一 PX4 freshness 门与 N07 evaluator 判定，不抬阈值。
