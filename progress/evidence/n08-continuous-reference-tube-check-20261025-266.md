#266：按真实样条和连续余量判定 N08 试验管道

## 修复

旧 watchdog 将 B-spline 控制点凸包直接作为实际路径。#265 保存的控制点凸包最大侧／垂向偏离为 5.072 cm，超过原 5 cm 管道；但真实曲线与边界有约 2.42 mm 余量。

新增 `certify_trial_reference_tube`：用 de Boor 计算真实曲线，在每个不超过 1 mm 的空间间隔采样；用导数控制多边形给出的全曲线最大速度，乘半采样时间，作为采样点之间的最大位移上界。只有每个采样点对前后 x 边界和侧／垂向圆柱边界的余量均大于该上界，才接受整条曲线。原限制保持：前向 x 相对起点在 `[-0.05, 0.65] m`，侧／垂向联合半径 `0.05 m`。采样不足或余量不足继续 fail closed。

N08 执行器现在将这项记录附加到每个接受的 live spline certificate；tube 拒绝会写入 `live_spline_rejections`，并以 `reference_curve_left_certified_trial_tube` 说明实际曲线拒绝原因。EGO 上游、速度 profile、N05 或定位门没有改动。

## #265 样条复算

对 #265 已保存的真实 Bspline 消息和起点运行新证书：

- 通过；采样点 1153 个，最大采样间空间距离 `0.00099914 m`。
- 导数控制多边形速度上界 `0.0809306 m/s`；任一点到最近采样点的最大位移界 `0.00049957 m`。
- 最小采样边界余量 `0.00241984 m`，超过带数值余量的连续要求 `0.00049957 m`。
- 样条范围：前向 x 偏移 `0.00148477–0.60000000 m`；侧／垂向最大偏离 `0.04758016 m`。

这是证书函数对归档曲线的离线复算，不是实际 EGO 飞行通过证据。下一项须在全新 N05 身份中重做 mission，确认 live spline 采用新证书并完成实际制动、原地 yaw 与前向返航。

## 定向回归

扩展 `tools/test_n08_trial_gate.py`，覆盖 #265 控制点凸包超限但实际曲线在原管道内、实际曲线越界、采样过稀导致连续余量无法证明而 fail-closed 三种情况。命令及结果：

- `PYTHONPATH=tools python3 -m unittest tools.test_n08_trial_gate`：6 tests，全部通过。
- 在固定容器 `d435i-vins:dev` 中 source ROS 2/install 后运行同一 N08 定向测试：6 tests，全部通过。
- `PYTHONPYCACHEPREFIX=/tmp/n08-pycache python3 -m py_compile tools/n08_trial_gate.py tools/run_n08_braking_trial.py tools/test_n08_trial_gate.py`：通过。
- `git diff --check`：通过。
- `python3 -m json.tool`：milestones 和 #264/#265/#266 JSON 证据语法通过；`python3 tools/project_status.py`：`Structure/design check: PASS`（非构建或SITL证据）。

仅 Python 工具代码更改，没有改 ROS package 或 EGO C++ 源码，因此未运行 ROS package build。SITL 对本次执行器更改的验证尚待 #267。
