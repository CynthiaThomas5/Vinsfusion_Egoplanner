# #103 N06 单轴平移入口观察 pilot

日期：2026-10-23。用户以`codex resume --last`恢复Goal完成模式，指定范围N06；N06/S4仍`in_progress`，`next_goal=N06`。

## 约束

- 仅单D435i未武装sensor-fixture仿真；PX4、bridge、controller、traj_server、setpoint与flight关闭。
- 保留unknown fail-closed、N05包络／预算、N06全部验收标准及工作区既有用户改动。

## r28结果

wall纹理surround内执行单轴X后退约2.394m后返回，VINS健康和MapStatus identity全程稳定。三张匹配fresh snapshot在actual VINS pose复算body球和terminal hold球均为raw free；实时body sphere请求一次返回`no_fresh_fused_depth`。默认planner目标`(+0.5,0,+0.5)m`有5个occupied terminal-hold cells，EGO正确拒绝，未产生曲线或迟到曲线。对同一快照离线验证的lateral `(0,+0.6,0)m`目标与直线body sweep为free，供下一次planner-only probe使用。详细结论见[#103 evidence](../../progress/evidence/n06-translation-entry-pilot-20261023-103.md)。

## 下一步

r29复用wall scan profile和场景，唯一planner变量为目标offset：实际VINS起点向Y正向0.6m，其他坐标不变。三张快照后手动执行自定义probe，runner默认probe仍另存。需要实际EGO生成当前map identity下的完整曲线，方进入两布局handoff与故障矩阵；如果只得到safe rejection，继续记录，不将N06标为通过。
