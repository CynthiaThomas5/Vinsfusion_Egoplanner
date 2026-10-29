#269：增加首个 EGO 目标前的垂向沉稳条件

## 目的与唯一变量

#267/#268 在首条 EGO 曲线开始时分别记录到约 0.01970/0.02304 m/s 的 PX4 local-position 垂向速度；对应样条偏差分别为 4.749/5.265 cm。两次相关性不足以建立因果。本子项只增加首个目标前的垂向速度条件，检验曲线是否在更稳定的初始速度下留在既有 5 cm 管道内。0.01 m/s 是运行门控假设，不改曲线验收阈值、速度 profile 或 N05。

## 代码变化

- `tools/n08_trial_gate.py`：增加 trial 起飞沉稳 helper，保留总速度 `<0.03 m/s`，另要求 `|vz|<0.01 m/s`。
- `tools/run_n08_braking_trial.py`：起飞后要求新条件连续稳定 1 s，20 s 上限不变；记录等待时长、速度阈值、最大速度与末样本，以便复核。
- `tools/test_n08_trial_gate.py`：添加新旧速度条件、速度边界与非有限输入回归。

## 验证与运行结果

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -m unittest tools.test_n08_trial_gate`：12/12通过。
- 对 gate、runner、测试文件执行 Python 内存 `compile(source, filename, 'exec')`：通过。
- SITL run `n08-20261025-269-vertical-settle` 未进入 mission。N05 支架扫描完成 10/15 阶段，在回程第11阶段将 locator 锁存为 `normalized_cost_exceeded`，reported 1.06881249 > 现有 1.0 健康界。没有 N05 post-release/current-area 准入、offboard、起飞或 EGO goal，因而尚未验证新增沉稳条件。
- 已直接读回 bridge `DISABLED/control_enabled=false/armed=false/landed=true`、PX4 `arming_state=1`、LandDetector `landed=true`；支架脱离且模型不存在。`bash tools/project.sh stop n08-20261025-269-vertical-settle` 返回 0，docker 容器退出码 0。
- 原始 VINS 归档重算 normalized cost 最大 0.67345692；未包含能解释状态报告 1.06881249 的匹配样本，精确触发观测尚缺，不能进一步归因。未更改 N05/VINS 门限。

## 下一步

#270 用新 epoch 和相同 `n08_far_small_pitch_view` 完整走 N05，维持所有准入阈值。如果 fresh release gate 通过，执行 #269 gate 再看首条 EGO 曲线证书；如果再次因 normalized-cost 锁存，则先补触发瞬间状态／指标归档，不绕过门控。N08继续保持 `in_progress`。

运行证据：[报告](../evidence/n08-vertical-settle-prerequisite-refusal-20261025-269.md)、[结构化结果](../evidence/n08-vertical-settle-prerequisite-refusal-20261025-269.json)。本记录对应对话：[摘要](../../collaboration/dialogues/2026-10-25-269-n08-vertical-settle-gate.md)。
