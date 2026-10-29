# 2026-10-26 #312：N08 rear scan SITL 拒绝

- 目标：以单变量比较验证把支架第 7 段回程从 60 s 延长至 100 s 是否减少定位健康锁存。
- 改动：新增慢返程 profile；其他阶段（含 12 s 下降）、传感器、定位健康阈值、地图和空间／速度门不变。
- 静态验证：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_preflight_scan`，43/43 通过；`python3 tools/project_status.py` 结构检查通过；JSON、shell 语法和 `git diff --check` 通过。
- SITL：`N05_KEEP_SIM=1 D435I_PLANNER_CONFIG=config/components/mapping/n08_low_speed_trial.json bash tools/run_n05_preflight_layout.sh n08-cancel-highspeed-prescan-20261026-312 n08_overhead_calibration n08_overhead_free_sector_negative_y_rear_short_hold_slow_return_slow_descent`。
- 结果：第 7 段返程和后向观察／回正通过；第 14 阶段下降约 5.1 s 后 `normalized_cost=1.005560>1.0` 锁存，扫描 14/17 阶段。没有 release gate 或 mission，因此不计 N08 飞行。
- 安全：夹具已脱离且 Gazebo model list 无 fixture；独立 6 s PX4/bridge 读回 disarmed、landed、control disabled，控制输入 topic 零样本；仅停止 #312，container exited 0。
- 后续：结合 #248（20 s）、#307（8 s）与 #312（12 s）停止下降时长微调。#313 将把低位回收安排在最后后向视角之前，并在低位以轻微上仰观察，以验证下降后置是否是健康代价升高的必要条件；同身份 N05 与实时几何门限不变。
- 证据：[运行报告](../evidence/n08-rear-scan-health-refusal-20261026-312.md)、[机器摘要](../evidence/n08-rear-scan-health-refusal-20261026-312.json)、[对话摘要](../../collaboration/dialogues/2026-10-26-312-n08-rear-scan-health-refusal.md)。
