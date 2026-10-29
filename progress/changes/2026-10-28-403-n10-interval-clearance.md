# N10.3/#403 物理步间净空界

关联对话：[2026-10-28-403 N10 净空评估](../../collaboration/dialogues/2026-10-28-403-n10-interval-clearance.md)

## 改动

- 新增离线 evaluator，按 Gazebo 模型原点真值速度/pose 计算；将真值到 `base_link` 的 0.24 m SDF 偏移应用到采样几何和旋转半径。
- 从 X500/D435i、PX4 Gazebo motor/ESC 插件与世界物理步推导保守线/角加速度界，并在 #398 每个 4 ms 区间复算全机包络净空。
- 接触分类严格匹配配置允许的两个滑橇碰撞体；其他碰撞或空碰撞对不被计入允许接触。对接触事件与独立接触 evaluator 做 run/goal/epoch/runtime 身份和终态交叉检查。
- PX4 来源校验改为 runtime dependency lock → PX4 revision → Gazebo submodule gitlink/manifest → 模型/插件文件哈希链；如实注明 #398 未直接记录 x500 SDF 的单次 SHA。
- 新增 7 项专用单测，保留 #398 原始数据和控制行为不变。

## 验证

- `PYTHONPYCACHEPREFIX=/tmp/n10-pycache-20261027 python3 -m py_compile tools/debug_truth/evaluate_n10_interval_clearance_bound.py tools/test_n10_interval_clearance_bound.py`：通过。
- `PYTHONPYCACHEPREFIX=/tmp/n10-pycache-20261027 python3 -m unittest tools.test_n10_interval_clearance_bound tools.test_n10_clearance tools.test_n09_contact`：20 项通过。
- `PYTHONPYCACHEPREFIX=/tmp/n10-pycache-20261027 python3 tools/debug_truth/evaluate_n10_interval_clearance_bound.py artifacts/runs/n10-20261027-398-speed040-integrated-calibration`：退出 0；24,627 个无接触物理步区间全部为正，最小保守界 0.174355 m；816 个接触区间仅为允许滑橇接地，独立评估禁止接触数为 0。
- `git diff --check`：通过。

## 限制与下一步

这关闭的是 #398 记录下的空气中物理步间净空方法缺口；着陆接触单独核验。该结果不含地图、定位、跟踪或制造误差，不构成最终验收阈值。没有运行 SITL、没有修改在线门限，也不抵扣冻结后的正式次数。下一项 #404 使用 #402 source-stamp observer 做综合校准，继续补 live 覆盖快照、场景误差/净空关系、资源/队列和一类缺证据故障。一次性紧急 disarm 授权已消耗，后续只按正常受控终止路径核验。
