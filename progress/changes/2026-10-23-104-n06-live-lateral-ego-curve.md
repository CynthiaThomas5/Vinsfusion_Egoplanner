# 2026-10-23 #104 N06 wall live lateral EGO curve

对话摘要：[N06 live lateral EGO curve](../../collaboration/dialogues/2026-10-23-104-n06-live-lateral-ego-curve.md)

## 结果与记录

- r29复用r28单轴X观察流程。2,015条LocalizationStatus全部有效，MapStatus保持单一ready identity；三张fresh snapshot source/fusion age均小于0.15／0.05秒。
- 自定义compute-only目标相对VINS起点`(0,+0.6,0)m`，在fresh epoch/map_id下由实际EGO发布一条匹配B-spline。完整曲线证书为`reason=free`、45次查询、0.430ms，0 faults、0迟到曲线。运行图没有控制节点／topic。曲线哈希`b7a29c...68cdea`。
- 同一snapshot-03 raw复算body球2,219 free、hold球4,862 free；lateral目标hold同为4,862 free，直线body sweep 25次查询全free。自定义probe的起点raw-query服务仍一次返回`no_fresh_fused_depth`；snapshot raw和EGO实际full-curve证书通过，不能把单次服务响应写成free。
- Runner内置default目标仍以`full_curve_terminal_hold_occupied`正确拒绝，其终端hold球含occupied体素；custom positive curve和default fail-closed probe分别保存在run目录。
- 证据报告／机器报告为 [#104](../evidence/n06-live-ego-lateral-curve-20261023-104.md)；原始产物见 `artifacts/runs/n06-20261023-wall-r29/`。Runner exit0并确认清理。

## 下一子项

N06.7 r30在`corridor_box_column`第二布局复用相同X后退／回程观察流程，重新取得fresh snapshots；从实际snapshot筛选后退方向目标，仅在起点body、terminal hold和完整body sweep均精确raw free时运行planner-only probe。走廊宽约1.5m，terminal-hold半径约0.981m，因此不假定走廊内可保持，目标需位于能完整容纳hold的开放区域。无safe candidate就不发goal。N06原双布局、hold、handoff和故障拒绝出口未变。

## 限制

Wall layout下当前只取得一条actual EGO curve；corridor layout及曲线活动期的map freshness、hold／emergency hold、replanning handoff、新障碍／wrong identity／stale-query／late-curve矩阵仍未完成。N06/S4与`next_goal=N06`继续保持未通过。
