# P5 无目标悬停与 VINS 时间／代价复测 #181

## 改动与行为

- 在独立 PX4 SITL 副本中沿用 canonical `vio_closed_loop` stack；run-local VINS overlay 记录双目图像回调到成对等待时间、特征跟踪耗时和首次质量门越线时 Ceres 分组评估耗时。
- 新增无导航目标悬停探针：仅通过 `uav_px4_bridge/enable_offboard` 请求起飞与落地，悬停期间不发送 action goal，不增加 PX4 控制话题发布者。所有额外 VINS 插桩只在 #181 build/run 副本内，canonical vendor 源和依赖补丁未改。
- #181 独立目录与遥测、真值隔离图、ULog 的路径和 SHA-256 见 [验收证据](../evidence/p5-vio-hover-cost-timing-20261019-181.json)。

## 结果

SITL 在无目标条件下保持 `ACTIVE` 20.011 秒，悬停窗口内 `normalized_cost` 中位数／P95／最大值为0.518／0.537／0.544；固定单次 SE(3) 对齐的 hold 子集位置误差 RMSE／P95／最大值为7.25 mm／12.3 mm／13.8 mm。411组双目配对的时间戳 skew 为0，左／右图像 callback-to-pair age P95 为23.9／1.94 ms，`trackImage` P95 为9.06 ms。

悬停结束并由桥接器进入 `LANDING` 后，仿真约2.51秒墙钟首次越过原 `normalized_cost=1.0` 质量门（1.0164）。单次 Ceres 分组评估用时0.189506 ms，视觉／边缘化／IMU cost 占比61.65%／38.08%／0.28%，分组和误差约`1.14e-13`。PX4 最终 `LANDED`、解除武装、`failsafe=false`。本轮越线发生在主动降落阶段，不说明此前运动目标 run 的越线根因；1.0 门限未改变。

## 验证

- run-local Jazzy build：`camera_models` 与 `vins` 2/2 包构建并安装；SITL runtime 包前缀指向独立 timing overlay。
- #181：VINS、localization、EGO、PX4 bridge 与 Gazebo SITL 运行完成；悬停探针 PASS、真值只读采集90.012秒并解析924条遥测、3,021条真值、12,210条 IMU，输出有限且无解析错误。
- graph 检查确认 `/debug_truth/base_odometry` 唯一订阅者为 `raw_vins_readonly_probe`，`uav_px4_bridge` 没有真值订阅；四个 PX4 控制输入话题在运行图中各只有一个发布者，且为 `uav_px4_bridge`。无 `/navigation/navigate_to_pose` goal 被派发。
- `bash -n`：run launcher 和容器 wrapper PASS；`python3 -m py_compile artifacts/runs/p5-px4-vio-ego-hover-20261019-181/run_vio_hover.py` PASS。
- `python3 tools/evaluate_vio_quality_alignment.py ...`：完整探针窗口476组配对，位置 RMSE/P95/最大0.586/1.715/2.766 m；悬停子集统计另由同一固定对齐 timeline 计算。完整窗口含起飞、落地和门控后退化，不能当作悬停误差。
- 运行输入、输出、run-local 源码、VINS binary、PX4 binary 和 ULog 的 SHA-256 见证据 JSON；阶段结构、回归测试与 `git diff --check` 在本记录落盘后复核。

## 局限与下一步

- 只完成一次 no-goal dwell；质量门在下降段越线，且完整 capture 的后段质量与位置误差快速恶化。图像队列龄与前端耗时未测量 sensor-to-estimator 端到端延迟，也不能定位具体坏帧或轨迹。
- 单次悬停不构成目标到达、避障、地图快照、重复冷启动、长时运行或最终 P5 证据。P4/P5 仍进行中，P6 未开始，GOAL A–H 未完成。
- #182 独立复测在 Offboard 信号失联保护后中止，没有完成悬停。下一步先调查 bridge→PX4 OffboardControlMode/TrajectorySetpoint 时间线及 timesync 源戳，再决定是否重跑；不基于单轮数据调门限。

## 对话摘要

[P5 无目标悬停与 VINS 时间／代价复测](../../collaboration/dialogues/2026-10-19-065-p5-hover-cost-timing.md)
