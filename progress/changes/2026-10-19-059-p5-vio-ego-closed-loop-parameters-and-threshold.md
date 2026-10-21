# P5 VIO–PX4–EGO 参数化诊断与质量门复核

## 改动

- `config/components/px4_bridge/vio_closed_loop.json`：VIO-only PX4 attitude future-stamp 上限从 0.05 s 调整为 0.065 s，以覆盖 #168 实测 0.053930 s 的提前戳；该值仍为 PROVISIONAL。共享/debug_truth profile、stale/receipt 与定位质量门保持原值。
- `tools/test_px4_bridge_vio_profile.py`：预期 VIO profile future-stamp 上限为 0.065 s，shared/debug_truth 仍为 0.02 s。
- 新增 #160–#171 轻量报告，保存所引运行报告、健康 trace、run-only 参数与 truth graph 文件的 SHA-256；补充对话摘要。
- 新增 `vio_closed_loop_ego_px4.launch.py`，按 config/SDF 参数生成 session 并组合真实 VINS、定位、mapping、EGO、navigation 与唯一 PX4 bridge；启动配置 helper 检查输入源、topic/drone id 和 D435i 相机几何。包清单声明 launch、VINS 与 localization 依赖；planner 的初始 FSM waypoint 保存在唯一配置源。
- `progress/CURRENT.md`、README 与 P5 evidence index 指向最新证据；P5 仍为 in_progress。

## 运行结果

#160/#163/#166 到 ACTIVE 并发目标后分别因 normalized_cost 1.12157/1.16979/1.66387 中止；这些轮次的 run-only EGO 使用 upstream 默认规划参数。#168 首次完整传入项目 EGO 参数与 D435i SDF 内参，但 50 ms future 容差被 attitude 的 53.930 ms 未来戳超出，随后安全降落。#170 在 65 ms profile 下通过定位/PX4 稳定门、启动 mapping/EGO、进入 ACTIVE 并发送纯 x 方向 0.5 m 目标；没有 future-age landing transition。首次质量超限为 1.159354，记录到的各输入年龄仍处既有门限内，随后 action 失败并安全落地、解除武装。canonical launch #171 在固定 Jazzy 新 install 中启动全部九个 ROS 节点，稳定门与 goal dispatch 通过；normalized_cost=1.011447 后按同一质量门 fail-closed，安全落地解除武装，末态 VehicleStatus failsafe=false。#171 记录160条 READY 和1条 flag-4命令，控制输入topic各一个发布者。该值不证明实际 VIO 误差。#170/#171 run reports 显示 PX4 控制输入话题各只有一个发布者，bridge graph 未订阅 debug_truth。

## 验证

- `python3 tools/test_px4_bridge_vio_profile.py`：7 tests，PASS。
- `python3 tools/test_vio_ego_bringup_config.py`：4 tests，PASS。
- `python3 -m py_compile ...`：PASS。
- 固定 Jazzy 镜像新 build/install/log 目录依赖构建：14 包通过；日志在 `artifacts/runs/p5-vio-ego-launch-build-20261019-02/log/`。
- `ros2 launch ... --show-args` 与 ROS_DOMAIN_ID 219 隔离 launch smoke：9 节点启动并经 SIGINT 清理。
- `python3 tools/project_status.py`：PASS；只代表结构/配置一致性。
- `git diff --check`：PASS；本轮涉及文件的行尾空白检查也通过。
- #171 canonical-launch SITL：稳定门通过、goal 派发，normalized_cost=1.011447 后因 `localization_normalized_cost_exceeded` 中止，`landed_and_disarmed=true`、末态 `failsafe=false`；不是成功导航或 P5 验收。

## 限制与下一步

65 ms 值目前有 #170/#171 两轮后续复核，仍为 PROVISIONAL。定位 quality guard `max_normalized_cost=1.0` 不变；尚无起飞/运动期间 normalized-cost 与独立位姿误差的相关性、重复到达、障碍净空、地图快照或长时验收。canonical VIO→mapping→EGO bringup 已接入并在 #171 启动验证；后续采集对齐质量/运动/独立误差时间线后继续。

## 对话摘要

[2026-10-19 P5 VIO–PX4–EGO 参数与质量门复核](../../collaboration/dialogues/2026-10-19-059-p5-vio-ego-closed-loop-parameters-and-threshold.md)
