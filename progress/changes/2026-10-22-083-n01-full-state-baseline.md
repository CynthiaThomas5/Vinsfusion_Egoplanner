# #083 N01 原始 VIO 全状态误差与漂移基线

[对话摘要](../../collaboration/dialogues/2026-10-22-083-n01-full-state-baseline.md)。持续 Goal 范围为 N01；不设默认 30 分钟截止。

## N01.1：现有记录与坐标审计

既有 #057、#069、#070、#072、#074 运行目录保存了 raw VINS 位置／四元数和 Gazebo 真值位置／四元数；#069 等 drift profile 已含静止、缓慢平移、回返、yaw、升降和阶段结果。原始 `fixture-odometry.jsonl` 没有 VINS `twist.linear`，也没有接收时刻；已有结果不能独立证明速度，也不能给出源龄和接收间隔。

从 `simulation/models/x500_d435i/model.sdf` 查明 `/debug_truth/base_odometry` 的 `robot_base_frame` 是 `d435i_link`；`simulation/models/d435i/model.sdf` 中 IMU sensor pose 为零；`tools/generate_vins_config.py` 将 VINS body frame 设为 `vins_<epoch>_imu`，且模型 rig body 为 `d435i_link`。因此 raw VINS IMU 原点与 Gazebo 真值点重合，不能将 `base_link` 安装偏移再次加到该真值。#057／#069 原有绝对误差数值已在相应报告顶部标为待更正；原始记录仍保留。

## N01.2：实现

- `tools/probe_preflight_scan.py` 仍只读订阅 raw VINS／optimized odometry；raw 记录新增 world-frame `velocity_xyz`、source frame 与 IMU child frame、仿真时钟回调接收戳和 `time.monotonic_ns()` 回调接收戳。没有增加任何 ROS／PX4 控制发布者。
- `tools/debug_truth/record_fixture_truth.py` 记录独立 Gazebo source truth 原有 pose，并额外记录 monotonic 接收时刻；真值仍不发布到定位／规划／控制链。
- 新增 `config/components/simulation/vio_full_state_baseline.json` 固定对齐、差分窗口、插值边界、RPE 窗口及运动范围。
- 新增 `tools/debug_truth/evaluate_vio_full_state.py` 输出同一初始刚体对齐下的 ATE、姿态误差、世界速度向量误差、1／5／10 秒平移／旋转 RPE、源龄、回调间隔、覆盖与拒绝数、运动支持范围；通过基座速度差分及 `ω×r` 重建核对 IMU 点速度，不重复应用安装偏移。
- `evaluate_fixture_odometry.py` 与 `evaluate_odometry.py` 的运行入口改用同点 truth-to-IMU 零平移；通用函数仍允许显式非零杆臂供其它真值参考场景使用。
- 新增 `tools/test_vio_full_state_baseline.py` 合成覆盖单次对齐、RPE、独立速度输入、杆臂运动学、缺字段、错 frame／epoch 与时钟回退。

## 验证

- `python3 -m unittest tools.test_vio_full_state_baseline -v`：3 项通过。
- `python3 -m unittest tools.test_fixture_odometry tools.test_odometry_evaluation tools.test_return_drift -v`：12 项通过。
- `PYTHONPYCACHEPREFIX=/tmp/d435i-n01-pycache python3 -m py_compile ...`：语法检查通过。首个默认 py_compile 写缓存时遇到仓库既有 root-owned `__pycache__` 权限拒绝，改用 `/tmp` 缓存后通过，未更改该目录权限或内容。
- `bash tools/project.sh test`：202 项 Python／C++ 探针回归通过；独立 ROS action 集成通过，250Hz 时钟下 pose receipt age 最大值 0.053s。
- 本轮没有修改 ROS 算法／消息／参数／第三方代码，未重建 ROS／PX4；上述是采集工具／离线算法测试，不是 N01 实际仿真证据。

## N01.3 实测与结论

- 在固定 protocol／runtime contract 下采集 3 个不同 VINS epoch：`...-01`、`...-03`、`...-05`；三个运动记录均完成 23 个阶段、三次返回和独立 truth 配对。#01 的采集器退出成功；#03／#05 的 result 保留 `failed`（detach 后 remove RPC 未确认），但独立只读 cleanup audit 均确认附件已 detached、Gazebo pose 清单中支架不存在、PX4 DISARMED 且 landed。汇总器只对这一特定错误接受完整测量，并要求 audit 哈希覆盖原始 result／stage／trace／runtime／protocol；未改写 failed 记录。
- #02 因 VINS `normalized_cost_exceeded`（1.20598）在第 11/23 阶段停止，已安全降回地面、拆架和关闭；不计入完整 epoch。#04 在第 0/23 阶段因 localization receipt age 0.520s 与 optimized odometry receipt age 0.599s 触发既有 0.500s stale 守卫；健康 cost 仍约 0.191。现场无支架运动，cleanup audit 确认地面、DISARMED、移除后安全关闭；不计入完整 epoch。两轮失败原样保留。
- #05 有 1 个 raw source interval 为 0.264s，高于 0.200s 插值支持间隔；评估器没有跨该间隔插值，coverage 报告超限计数，1／5／10s RPE 分别明确报告 11／34／66 个拒绝窗口。该间隔是被量化的覆盖缺口，不伪装为连续观测；协议用于逐窗口拒绝和报告，不作为整段 epoch 的额外全局通过门。
- 三个完整测量 epoch 共用语义 protocol hash `8e8c6ae6…baf433` 与 runtime contract `4e2b88bd…354478e`。离线评估器增加 2ns 的纳秒舍入容差，统一复评全部 epoch；仅消除 `200000001ns` 与配置 `200000000ns` 的整数表示误差，原始数据和 protocol 字节未变。最终评估器 SHA-256 为 `5fa01f7f…318b4d23`。
- 同点重算历史 #057／#069 后，旧报告中的绝对位置／yaw 误差和累计返回数值已更正；旧 JSON 与原始记录保留。它们缺少 raw VINS twist／回调接收时刻，不替代三次全状态 fresh epoch。
- `summarize_vio_full_state.py` 现在明确验证三 epoch 唯一性、协议／runtime 一致、RPE／returns／哈希与 post-detach 独立 cleanup evidence，并输出 source-gap 超限数及每个 RPE 窗口候选／支持／拒绝数；合成回归覆盖合法 cleanup audit 与拒绝不安全 audit。没有更改定位、健康阈值、PX4 控制或采集运动协议。

汇总结果、逐 epoch 指标、排除记录和限制见 [N01 证据报告](../evidence/vio-full-state-baseline-20261022-083.md) 与机器可读汇总 [summary.json](../../artifacts/runs/n01-vio-state-20261022-083-checks/summary.json)。N01 仅证明报告列出的低速未武装支架运动范围，不表示定位达到最终精度门限、自由飞行通过或真实 D435i／机载性能合格。

## 最终验证

- `python3 -m unittest tools.test_vio_full_state_summary -v`：5 项通过。
- `bash tools/project.sh test`：208 项通过；ROS action／250Hz clock 集成通过。
- `python3 tools/project_status.py`：Structure/design check PASS；输出提示 80 个可选历史 artifact 链接缺失。该结构检查不代表 ROS build、SITL 或实机验收。
- `git diff --check`：通过。
