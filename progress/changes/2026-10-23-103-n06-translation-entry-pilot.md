# 2026-10-23 #103 N06 translation entry pilot

对话摘要：[N06 translation entry pilot](../../collaboration/dialogues/2026-10-23-103-n06-translation-entry-pilot.md)

## 结果与记录

- r28在同一wall与纹理surround使用单轴X后退／回程；truth最大后退2.3945m、回程残差0.0106m，yaw为0°。2,019条LocalizationStatus全有效，444条MapStatus保持同一ready identity。
- 三张匹配fresh snapshot的source/fusion age为0.099–0.145／0.039–0.042秒；错误epoch/map_id拒绝通过。以actual probe VINS位置复算，body球三张均2,195 free／0 unknown／0 occupied，terminal hold球均4,923 free／0 unknown／0 occupied。这是wall layout下的raw map入口正向证据。
- live body球服务请求单次返回`no_fresh_fused_depth`。内置planner目标`(+0.5,0,+0.5)m`的hold区含5个occupied cells；EGO正确以`full_curve_terminal_hold_occupied`拒绝，55次certificate query、0曲线、0迟到曲线。控制free graph检查通过。
- 用同快照按生产闭格球与连续扫掠函数确定`(0,+0.6,0)m` lateral target的hold和直线路径均free；这是planner目标选择的离线候选，不是实际EGO曲线。逐项结果在run artifact `n06-body-hold-replay.json`。
- 完整快照、输入、运动真值、probe和哈希见 [#103证据](../evidence/n06-translation-entry-pilot-20261023-103.md) 与 [机器摘要](../evidence/n06-translation-entry-pilot-20261023-103.json)。runner exit0，容器和匹配进程已停止。一次全地图候选链穷举因计算开销中止；本次未声明全地图离线曲线链。

## 下一子项

N06.6 r29复用同一观察profile重建fresh map，只改变planner-only goal为live VINS起点`[0,+0.6,0]m`；实际目标和路径已在r28快照中逐格检查为free。运行runner后，在snapshot-01和snapshot-02间隔内执行自定义probe，默认probe另行保留。判据是实际EGO在稳定身份下发出goal匹配的B-spline full-curve certificate，且故障后无迟到曲线；不接controller、traj_server、PX4或setpoint。详见 [CURRENT](../CURRENT.md) 与 [N06总报告](../evidence/n06-full-curve-layout-review-20261023.md)。

## 限制

r28只覆盖wall layout的unarmed sensor fixture。实际起点body与hold的raw map查询为free，但该run live服务的一次sphere query没有fresh response，且选择的default elevated target因occupied hold被正确拒绝。corridor layout、EGO正向curve、hold状态期间覆盖与replanning handoff仍未通过。
