# N08.2z #236：证书同时检查 EGO 逐轴速度界

## 问题与依据

#231 compute-only run 的 derivative-control-hull Y 分量上界为 0.08157 m/s。配置 `max_velocity_m_s=0.075`，EGO `UniformBspline::checkFeasibility` 按单轴检查，允许值按 `limit_vel * (1 + feasibility_tolerance) + 1e-4` 计算，其中 tolerance=0.05；本 profile 的逐轴上界约 0.07885 m/s。现有 N08 curve certificate 只比较三维向量上界与 0.15 m/s，未将逐轴超限纳入 `speed_pass`，会留下错误的单维正向结果。

## 目标与范围

- 令证书同时要求 derivative control hull 的每轴绝对值上界不超过 EGO 当前逐轴可行性界，且三维向量范数上界不超过现有 0.15 m/s 门限。
- 门限从当前 launch 配置及上游 feasibility tolerance 原样实现；不改 EGO、PX4 或 planner 参数，不放宽 N08 exit，不影响 PX4 bridge。
- 新增合成回归，覆盖逐轴超限但向量通过、两个门都通过和向量超限。复用 #231 保存证据说明受影响结论，不重跑历史冷启动或 hover。
- 本子项仅做 evaluator/单测，无 SITL、无 compute-only 任务、无 XY。

## 完成标准

`tools/evaluate_n08_curve_certificate.py` 为每轴和向量上限分别生成通过项；组合 `speed_pass` 必须二者均通过；原有 map/identity/freshness/geometry 门和 `n08_execute_authorized=false` 保持不变。单测、Python compile、`project_status.py`、`git diff --check` 通过。

对话摘要：[dialogue](../../collaboration/dialogues/2026-10-24-236-n08-axis-speed-certificate.md)。


## 实施结果

- 新增 `certify_speed_bounds`。证书 schema 更新为 `n08-live-curve-certificate/v2`，单独输出逐轴和向量门并以二者 AND 作为 `speed_pass`。保持现有0.15 m/s向量cap、N05 raw-map geometry、identity/freshness及 `n08_execute_authorized=false` 不变。
- `max_velocity_m_s=0.075` 的逐轴限制严格复用 EGO `UniformBspline::checkFeasibility`：tolerance 0.05、epsilon 1e−4 m/s，得到0.07885 m/s。配置 qualification 文字同步说明已有两个门；没有更改 planner 参数或任何安全阈值。
- 新增 `tools/test_n08_curve_certificate.py`。命令 `python3 -m unittest tools.test_n08_curve_certificate tools.test_n08_compute_only`：7 tests passed。AST parse、`python3 tools/project_status.py` 和 `git diff --check` 通过。`py_compile` 因不能写入受保护的 `tools/__pycache__` 未完成；测试成功 import 新 evaluator，AST parse 通过。
- #231已有 Y derivative hull=0.08157 m/s，按新门应 fail per-axis；不重跑、不改写历史 run。完整报告与哈希见[证据](../evidence/n08-axis-speed-certificate-20261024-236.md)和[JSON](../evidence/n08-axis-speed-certificate-20261024-236.json)。对话摘要：[dialogue](../../collaboration/dialogues/2026-10-24-236-n08-axis-speed-certificate.md)。

#236完成的是证书正确性，不是 N08 运动/制动出口。下一子项 #237：待共享负载和仿真时钟推进稳定后，以 #235 同 profile 加只读 `/clock`、LocalizationStatus、optimized-odometry transition 记录重做支架扫描；N05 fresh gate 仍必须通过才启动 compute-only。
