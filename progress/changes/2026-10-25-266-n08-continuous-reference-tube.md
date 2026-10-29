# N08.266：连续 B-spline 试验管道证书

对话摘要：[2026-10-25-266](../../collaboration/dialogues/2026-10-25-266-n08-continuous-reference-tube.md)

## 改动

- 在 `n08_trial_gate.py` 添加基于实际 de Boor B-spline 的管道证书。
- 使用导数控制多边形速度上界约束采样间位移，保持 x `[−0.05, +0.65] m` 与侧／垂向联合半径 `0.05 m` 原标准；不确定时拒绝。
- N08 执行器把证书写入 live spline accepted/rejected 结果，删除以 control-point hull 直接等同实际轨迹的误拒。
- 在定向回归中固化 #265 实际样条，并检查曲线真越界及采样不足失败情形。

## 验证

- `PYTHONPATH=tools python3 -m unittest tools.test_n08_trial_gate`：6 tests passed。
- 固定容器 `d435i-vins:dev` 中运行相同定向测试：6 tests passed。
- `PYTHONPYCACHEPREFIX=/tmp/n08-pycache python3 -m py_compile tools/n08_trial_gate.py tools/run_n08_braking_trial.py tools/test_n08_trial_gate.py`：通过。
- #265 归档曲线：1153 点；连续最大间隔界 0.000500 m；最低余量 0.002420 m；5 cm 原限值内通过。
- `python3 -m json.tool`（milestones与#264/#265/#266证据）、`python3 tools/project_status.py`（结构检查）及 `git diff --check`：通过。
- 没有 ROS package／C++ 改动；全新 SITL 行为验证由 #267 执行。

## 限制与下一步

helper 回归通过不证明完整任务。#267 使用新 epoch、新鲜 N05 和相同 planner profile 执行实际 N08：如 live tube 通过，继续观察前向制动与 hold、原地转向 180°、转向后 fresh map 和前向返航；任一 gate 关闭即 fail-closed 并记录。
