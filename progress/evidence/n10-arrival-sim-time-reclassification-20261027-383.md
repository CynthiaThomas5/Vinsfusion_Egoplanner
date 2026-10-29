# N10.3/#383 到达驻留时间域复算

**结果：修复独立评估器并复算三份归档；三次旧 wall-time PASS 均未满足 GOAL F 的 3.0 仿真秒。** 本报告保留所有旧归档，不覆盖 `arrival-evaluation.json`，新结果写入每个 run 的 `n10-arrival-evaluation-simtime.json`。JSON详情：[机器报告](n10-arrival-sim-time-reclassification-20261027-383.json)。

| Run | 旧连续窗口（wall s） | 新窗口（sim s） | 位置最大误差 | yaw最大误差 | 3.0 sim s |
|---|---:|---:|---:|---:|---|
| #361 | 3.0187 | 2.2600 | 0.29581 m | 8.90° | FAIL |
| #376 | 3.1136 | 2.7800 | 0.29686 m | 3.16° | FAIL |
| #381 | 3.0551 | 2.3400 | 0.29842 m | 11.89° | FAIL |

评估器现在以 Gazebo source stamp 累计仿真秒；墙钟仅单独报告。真值点必须严格递增，连续判定最大采样间隔0.04 sim s；超过此间隔会打断驻留。位置与yaw必须同一采样同时达标，yaw按最短环绕角处理。新输出还把定位状态/日志记为观察字段，不用它们再加项目自定义健康拒绝。

新增6个边界测试通过，覆盖wall/sim分离、3秒仿真驻留、样本空窗、容差中断、yaw环绕和重复/回退时间戳。测试命令：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_arrival_evaluator -v
```

只读复算命令（分别在各run上执行，旧报告不覆盖）：

```bash
python3 tools/debug_truth/evaluate_arrival.py artifacts/runs/n10-20261027-361-quality-gates-removed-speed080-16m --output n10-arrival-evaluation-simtime.json
python3 tools/debug_truth/evaluate_arrival.py artifacts/runs/n10-20261027-376-gatefree-cylinder0-observation --output n10-arrival-evaluation-simtime.json
python3 tools/debug_truth/evaluate_arrival.py artifacts/runs/n10-20261027-381-vins-velocity-full-route --output n10-arrival-evaluation-simtime.json
```

**修复影响**：该变更没有修改任何飞行运行代码、目标、控制、速度、地图或健康策略。它纠正了独立离线验收的计时域，旧报告中“≥3s”的解读不成立；action native success 也不能替代真值3 sim s驻留。GOAL的3.0 sim s值不变。下一步用较长的native goal dwell保留额外实测时间，让真值位置/yaw联合窗口实际覆盖3.0 sim s，并更新唯一验收配置与判断器。当前N10仍未通过。
