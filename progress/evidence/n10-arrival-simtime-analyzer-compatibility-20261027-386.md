# N10.3/#386 到达评估器与校准脚本兼容修复

**结论：离线评估链已修复并重算 #385；原运行和旧归档未覆盖。** #385 冻结的校准脚本仍要求到达报告提供 `ground_rotation`、`ground_translation` 与最小位置误差字段；仿真秒版本评估器已改用新的联合窗口结构，原 driver 因 `KeyError: ground_rotation` 退出。

当前 [evaluate_arrival.py](../../tools/debug_truth/evaluate_arrival.py) 在只读报告中补回固定 SE(3) 对齐字段与最小真值误差。原脚本已复制并按 SHA-256 保存为 `artifacts/n10-prepared/n10-20261027-385-arrival-dwell4-retry/evaluate_arrival-frozen-v1.py`。#385 的 v1 `arrival-evaluation.json`、原失败日志及冻结校准脚本均保留。

新增输出 `arrival-evaluation-simtime-v2.json` 独立重算仍为 **PASS：3.32 仿真秒**，满足 3.00 仿真秒合同。独立 post-run adapter 输出 `n10-calibration-evaluation-simtime-v2.json`，分类为 diagnostic sample；它不是正式资格。

验证：

- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_arrival_evaluator -v`：6/6 通过。
- 两个 Python 文件的内存语法编译通过。
- 使用 `python3 -B tools/debug_truth/evaluate_arrival.py artifacts/runs/n10-20261027-385-arrival-dwell4-retry --output arrival-evaluation-simtime-v2.json` 复算通过。
- 使用 `python3 -B artifacts/runs/n10-20261027-385-arrival-dwell4-retry/n10_calibration_postrun_v2.py artifacts/runs/n10-20261027-385-arrival-dwell4-retry` 完成校准离线分析。

机器报告：[JSON](n10-arrival-simtime-analyzer-compatibility-20261027-386.json)。
