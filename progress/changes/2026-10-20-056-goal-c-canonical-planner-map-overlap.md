# GOAL C canonical EGO 绕障规划与地图单元对照 #304–#305

Related dialogue: [2026-10-20-056](../../collaboration/dialogues/2026-10-20-056-goal-c-canonical-planner-map-overlap.md)

## Change

- 使用 #297 全新 canonical EGO build/install，复用单 D435i、VINS、定位适配和在线 plan_env；没有启动 PX4、轨迹服务器或控制器。诊断目标为 VIO odom `(2.5, 1.4, 1.0)`，run-local 障碍布局来自既有箱体/圆柱场景。目标直线对箱体名义方向不变机体球的 SDF 净空约−0.435 m。
- #304 在 ready MapStatus 下派发目标并收到两条同 epoch B-spline。固定尺度单 SE(3) 离线几何分析显示：首条曲线对箱体/墙面的名义球净空约+0.133/+0.073 m；第二条约+0.191 m/−0.028 m。第二条曲线仍距离 SDF 墙面约0.454 m，但比0.482 m名义机体球半径小约2.8 cm。requested-goal端点误差分别0.013/0.239 m。该几何评估没有执行任何轨迹。
- #305 复测了同一目标和场景，并在目标探针发出目标后调用 occupancy snapshot 服务。两条曲线再次复现：第一条箱体/墙面名义球余量+0.135/+0.074 m，第二条+0.193/−0.024 m。EGO实际运行参数 `obstacles_inflation=0.099 m`；该值是 provisional planner mask 半径，不覆盖名义机体球包络。
- #305 目标时间戳6.050 s；snapshot最近融合深度源戳7.195 s，服务耗时1.043 s，源戳落后目标1.145 s。目标时刻 MapStatus的深度转发数为24；服务完成时映射统计已到39→61。motion driver首个力指令在15.617 s，因此goal至snapshot期间场景保持静止，但快照仍不是精确同刻地图。
- 把每条中心线的1201个采样点映射到 #305 的 `snapshot-goal` 网格：traj 1有422个unknown/779个free样本；traj 2有655个unknown/546个free样本；两条均无样本位于occupied、inflated或地图外。后续静止视角快照仍保留大量unknown；运动后才继续转为free。由于无逐体素观测时间，只能说明目标后近时刻地图与路径存在这种关系，不能重建精确planning-time输入。
- #304/#305均有三时刻同epoch快照、身份拒绝和NPZ精确回读；全部运行无控制节点、控制topic或truth topic。精简结果见 [#304](../evidence/p2-ego-planner-detour-canonical-20261020-304.json) 和 [#305](../evidence/p2-ego-planner-goal-map-alignment-20261020-305.json)，原始数据在对应 `artifacts/runs` 目录。

## Verification

- `bash -n` 检查 #304/#305 容器与live脚本通过；planner、map-overlap和temporal分析脚本均通过 `python3 -m py_compile`。
- #304/#305 实际运行均使用镜像 `d435i-vins:dev`（与 #297 固定镜像ID一致）；VINS进入 valid/ready，EGO planner probe成功派发目标并记录2条B-spline。
- #305 的目标后快照和后续三份快照共享 epoch/map_id/frame；四份归档逐数组精确回读，epoch/map_id错误请求均拒绝。snapshot服务响应时间分别保留，目标后快照耗时1.043 s。
- 所有 temporal、trajectory、map-overlap分析文件中嵌入的来源SHA-256均重新计算匹配；GOAL C和里程碑状态均未改变。

## Limitations and next step

- 规划曲线没有交给 `traj_server` 或任何控制器执行，净空基于单次SDF采样及名义方向不变球，未包含机体不确定性、地图误差、跟踪误差和制动距离。
- truth位置在离线对齐窗口内没有变化；1.9 s静止窗口不构成独立地图到世界姿态标定。#305 snapshot源戳比目标晚1.145 s，地图没有逐体素观测戳。
- 两条路径的unknown与inflated分类只对目标后的快照成立；它们与此前 baseline unknown-as-free 源码审计相符，但本轮未修改第三方规划策略。
- 下一步审查既有 unknown-as-obstacle 候选patch，生成基于固定EGO commit和canonical patch序列的新候选补丁；同时把planner inflation作为 `config` 中明确 PROVISIONAL 的机体包络候选，独立构建并复测同一目标和目标后快照。数值未按GOAL F正式冻结；重复验证通过前不接入最终飞控组合。
