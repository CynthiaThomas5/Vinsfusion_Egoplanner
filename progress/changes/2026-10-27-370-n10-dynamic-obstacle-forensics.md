# #370 N10.3 动态障碍运行离线取证

## 改动

- 新增 #369 独立真值、EGO 命令、Gazebo SDF 与机体接触的离线相关报告：`progress/evidence/n10-live-obstacle-forensics-20261027-370.md` 和 JSON。
- 分别复算 action 成功前的 goal-feedback 时间窗与 action 后到落地的长保持时间窗；保留二者并标出不能直接合并。
- 更新 `progress/CURRENT.md`、N10 执行计划、milestones、`docs/n10-completion-plan.md` 和 N10 子目标汇总，保留 N10 `in_progress`。

## 结果

- #369 机体与静态圆柱的接触记录是真实非零：134 条，sim 99.652–100.280 s，最大穿透 0.000521 m。
- 接触时 EGO 参考 IMU 点与固定 SE(3) 对齐后的真值 IMU 点偏差约 0.519 m；此偏差可能消耗规划间距，但圆柱图像/occupied ROI 未记录，根因仍未证实。
- action 回报前的独立联合位置/yaw驻留为 2.200 仿真秒、2.759523 墙钟秒；到落地窗口为 267.040 仿真秒、342.001 墙钟秒，包含 action 后的 600 秒 ACTIVE 保持。
- 方箱采样净空扣减最大相邻样本包络运动后为 0.462698 m；此结果不抵消圆柱接触。

## 验证与限制

- 运行只读离线复算：`python3 tools/debug_truth/evaluate_n10_arrival.py artifacts/runs/n10-20261027-369-alignment-gates-removed-live-obstacle --output /tmp/n10-369-arrival.json`，完成；N10评估器返回诊断检查通过（目标到落地窗口）。
- 使用 Python 对该评估器结果另行限制到 `flight.json.goal_completed_source_ns`，得到 action 回报窗口联合达标 2.200 仿真秒／2.759523 墙钟秒。
- 接触几何复算使用同一固定 SE(3)、真值相邻样本插值和位置命令源时间；未做控制或真值反馈。
- 未修改飞行运行代码、阈值、配置或碰撞处理。N10.3 未完成；#371 只补齐静态圆柱感知/地图的只读观测证据。

证据：[报告](../evidence/n10-live-obstacle-forensics-20261027-370.md)、[JSON](../evidence/n10-live-obstacle-forensics-20261027-370.json)。
