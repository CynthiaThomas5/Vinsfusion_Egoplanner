# GOAL C 半体素墙面相位干预 #299–#303

Related dialogue: [2026-10-20-055](../../collaboration/dialogues/2026-10-20-055-goal-c-grid-phase-intervention.md)

## Change

- 在隔离生成的诊断场景中把大墙前表面从 x=3.00 m 平移到 x=3.05 m，等于当前0.10 m地图分辨率的一半；箱体、圆柱与运动加速度序列保持一致。x=3.00 m是名义栅格边界，x=3.05 m是邻接体素中心。未修改项目源 world 或 `src/vendor`。
- #299完成但三个快照比基线运动时相晚约1.4–1.9 s；#300驱动器错误地从run目录解析配置路径，未完成运动、没有快照；#301完成但首个快照早于首条运动命令，后两帧也早于基线约1.3–1.4 s。这三轮均不作为匹配时相因果证据。
- #302在 canonical EGO #297 新重建 install 下完成相位目标复测。源时相为首条force后1.748、4.157、6.863 s，与#295相差+0.065、−0.100、−0.067 s。三个快照共享epoch/map_id/frame，均精确回读NPZ并拒绝epoch/map_id错配；运行图中没有控制节点、控制topic或truth topic。
- 两轮原相位基线#295/#296都选择墙面局部x中心3.05→2.95→3.05 m；三轮平移run均选择3.05→3.05→3.05 m。#296首帧72个距离分析SDF超过0.10 m的墙点全部是x=2.95 m；#302三帧均无occupied中心超过该诊断距离，SDF中位/P95/最大分别为0.75/1.43/5.76 cm、0.72/1.58/6.63 cm、0.65/1.56/5.76 cm。这支持网格相位参与了侧选变化及阈值尾部，但不足以证明根因或排除其他地图误差／重影。
- 刷新 #298 视锥分析来源哈希，并重生成 #302相位对比报告，使其哈希清单包含最新 #298 报告。轻量证据见 [#303](../evidence/p2-map-grid-phase-shift-20261020-303.json)；完整空间／运行数据保留在各 `artifacts/runs/p2-map-voxel-snapshot-wall-phase-20261020-{299,300,301,302}`。

## Verification

- `python3 artifacts/runs/p2-map-voxel-snapshot-service-20261020-296/analyze_visible_wall_roi.py` — passed；独立核对其25个输入SHA-256均匹配，更新 #298 compact evidence。
- `python3 artifacts/runs/p2-map-voxel-snapshot-wall-phase-20261020-302/compare_wall_grid_phase.py` — passed；88个比较来源SHA-256均匹配，#302源时相与网格中心序列被重算。
- #302 runtime summary — 三次归档精确回读，epoch/map_id错配都被拒绝；无控制节点、控制topic或truth topic。此为planner-only地图诊断，不是目标规划或导航验收。
- 本轮只新增探索性证据，GOAL C和阶段里程碑状态未改变。

## Limitations and next step

- 匹配时相相位干预目前只有#302一轮；#299/#301不具备匹配捕获时相。单次相位改变不构成重复性或地图准确性验证。
- SDF用于离线评价；全程VINS/fixture-truth拟合的刚体变换不是独立标定。frustum ROI不处理遮挡和深度无效，快照没有每个体素的观测时间。
- 0.10 m距离线等于一个体素宽度，仅为诊断阈值；目前没有冻结导航ROI、覆盖、重影、unknown安全或净空标准，也没有运行planner目标、轨迹执行或控制。
- 下一步先依据 GOAL 与架构冻结评估ROI、覆盖/重影/unknown和净空边界，再使用独立姿态标定、多布局地图快照及canonical EGO无控制绕障试验验证；保持truth仅用于离线评估，不进入最终组合。
