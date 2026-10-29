# #105 N06 corridor 局部地图边界诊断与下一子项

对话摘要：[N06 corridor observation boundary](../../collaboration/dialogues/2026-10-23-105-n06-corridor-observation-boundary.md)

## 结果

- r30 runner自然exit0，runner／VINS／map运行清理确认；2,018条定位状态全有效，440条MapStatus单identity、ready。三张fresh snapshot和错误identity拒绝检查通过。
- 后退四个目标offset均因连续body sweep与terminal hold raw unknown被拒，未发送自定义goal。runner内置默认goal另行触发`full_curve_planning_failed`，0条curve／0 late curve，图中无控制消费者。
- 起点body raw free；snapshot-03当前terminal hold有16 unknown／25 occupied，不能归为可用hold。
- 原始ray replay显示首个扫掠4个unknown cell历史上被当前DDA逻辑的射线穿过；回程后的当前pose在x≈0。结合运行`local_map_margin=10`体素和`clearAndInflateLocalMap()`外界清unknown行为，推断这些cell超出约1m局部保留窗口后被清除。无逐帧occupancy历史，保留为源代码与运行参数支持的推断，不改raw unknown。
- snapshot source比input recorder末pose晚3.366／16.830秒（snapshot-01／03）；精确source-pose覆盖不完整，所有补充投影产物均说明限制。

## 下一子项

N06.8 r31将单轴sensor-only运动终点留在corridor入口外`x≈−0.8m`，扫描最远到`x≈−3.2m`；用同一个1m local-map margin覆盖入口外hold体积。新增profile使用分段持续时间，在不超过0.12m/s峰值的前提下从0退到−3.2再停于−0.8。所有raw body／连续sweep／terminal hold查询通过后，才向`+Y 0.25m`发planner-only EGO goal；否则不发送。原N06验收条件不变。

## 记录和验证

- 证据：[r30结果](../evidence/n06-corridor-observation-boundary-20261023-105.md)、[机器摘要](../evidence/n06-corridor-observation-boundary-20261023-105.json)。
- 运行产物：`artifacts/runs/n06-20261023-corridor-r30/`，含地图快照、inputs、默认probe、候选守门报告及离线DDA审计。
- 本次只更新进度／证据文档；未修改运行实现或安全参数。结构检查与`git diff --check`在文件写回后复跑并记录。
