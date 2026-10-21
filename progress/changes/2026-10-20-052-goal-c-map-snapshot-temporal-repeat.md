# GOAL C 第二布局独立 epoch 复测 #296

对应对话摘要：[2026-10-20-052](../../collaboration/dialogues/2026-10-20-052-goal-c-map-snapshot-temporal-repeat.md)

## 修改与行为

本轮没有修改项目源码或候选 patch。以 #295 的箱体／圆柱布局及完全相同的 world SDF 开展独立重复；更换 ROS domain、Gazebo partition 和 VINS epoch，继续使用同一运动 profile、候选 EGO 安装和三个快照门槛。分析报告比较两个 run 的独立固定尺度 SE(3) 对齐结果。

墙面中位 occupied voxel center 在 #295 与 #296 都呈现约3.03 m→2.96 m→3.03 m的时序模式。相邻快照偏移分别为 #295 的73.27/71.23 mm、#296 的68.38/67.07 mm；相应偏移量跨run相差4.89/4.15 mm，而匹配时刻中位位置差为0.63–3.52 mm。墙面前表面x=3.0 m恰位于origin=-12 m、0.1 m resolution的名义x栅格边界index150；一个在中心墙片的离线采样格上，边界距离中位/P95为#295 8.3/16.3 mm、#296 11.9/25.7 mm。这使cell-side量化成为可能解释，但未区分深度误差、可见点集合或其他mapping artifact，不能据此宣称存在或不存在ghosting。

#296 三份快照known voxel为16,247、21,730、22,069；raw occupied集合Jaccard为0.555、0.674。首帧2,067个occupied中心中有72个到最近SDF表面距离超过0.10 m，后两帧分别有2和5个；进一步定位显示72个首帧离群点均分配给大墙，范围约y=-2.80至-1.80 m、z=1.83至3.03 m，全部位于分析器既有中心墙面采样窗外（该窗不是正式验收ROI）。点均保留并报告。EGO无 `odom or depth lost` 告警且干净退出，但没有目标、轨迹或控制，因此不是planner验收。

## 验证

- `bash artifacts/runs/p2-map-voxel-snapshot-service-20261020-296/run-container-01.sh`：exit 0；三份快照共享新 epoch/map_id/frame，错身份请求被拒绝且NPZ逐数组回读一致；运行后无控制节点或truth/control topic。
- `python3 artifacts/runs/p2-map-voxel-snapshot-service-20261020-296/analyze_temporal_maps.py`：栅格身份、shape/dtype/计数、同epoch差分、固定尺度轨迹对齐和SDF分析通过。
- `python3 artifacts/runs/p2-map-voxel-snapshot-service-20261020-296/compare_same_layout_repeat.py`：确认 #295/#296 障碍物定义、world SDF哈希相同，epoch/map_id不同；生成的墙面位置重复性报告见 `same-layout-repeat-analysis.json`；首帧离群点空间统计见 `sdf-outlier-location-analysis.json`。
- 服务响应39.13–50.36 ms，源龄99–126 ms。静态检查、JSON与引用哈希、结构检查及 `git diff --check` 在收尾阶段复核。

## 局限与下一步

两轮相同布局重复了单栅格级墙面位置摆动，但首帧SDF离群点数明显高于后两帧。墙面恰与栅格边界对齐，故优先查证不同帧选择相邻格点的原因；首帧72个离群点都落在分析器既有中心墙采样窗外，且该窗口不是验收ROI。下一步按capture phase检查其可见性、原始深度投影和source-age，再定义可见ROI coverage与重复表面距离；尚不能冻结ghosting或覆盖阈值。下一步对matched capture phase计算有界可见表面的覆盖率和重复表面距离，解释首帧72个离群中心，再考虑正式GOAL C验收。候选patch 0021仍不在canonical依赖链，GOAL C保持 pending。

轻量结果：[证据](../evidence/p2-map-snapshot-temporal-repeat-20261020-296.json)；[运行报告](../../artifacts/runs/p2-map-voxel-snapshot-service-20261020-296/run-report.json)；[跨run分析](../../artifacts/runs/p2-map-voxel-snapshot-service-20261020-296/same-layout-repeat-analysis.json)。
