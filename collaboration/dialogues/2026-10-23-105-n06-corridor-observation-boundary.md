# #105 N06 corridor observation boundary

日期：2026-10-23。用户以`codex resume --last`恢复Goal完成模式，授权范围N06。

## 约束

- 单D435i sensor-rig仿真；不启动PX4、bridge、controller、traj_server、setpoint或飞行。
- 保留当前worktree所有已有修改；unknown fail-closed；不改N05包络／预算、N06验收条件或地图未知策略。

## 决定与结果

r30 corridor X后退／回程扫描保持健康，三张fresh snapshot身份匹配。候选后退`−0.8/−1.0/−1.2/−1.4m`均因相同首个sweep sample及terminal hold含raw unknown而没有选中，不发送自定义goal。runner默认probe另外发出`(+0.5,0,+0.5)m`，EGO返回`full_curve_planning_failed`、0 curve、0 late curve，control-free graph通过。body起点free，snapshot03 hold有16 unknown／25 occupied。

离线复算显示首个扫掠失败的4个unknown voxel在历史深度采集中被当前DDA逻辑的射线穿过；但扫描回到x≈0后，运行local_map_margin为10×0.1m，局部边界外会被clear成unknown。它解释了历史ray与当前snapshot的差别，是证据推断，不是raycast defect证明。snapshot-01／03 fused source比最后记录camera pose晚3.366／16.830秒，无法作精确source-time投影。细节见[#105报告](../../progress/evidence/n06-corridor-observation-boundary-20261023-105.md)。

## 下一步

N06.8 r31假设把sensor-rig终点留在corridor入口外x≈−0.8m，扫描最远到−3.2m后回到−0.8并停稳，可让局部地图保留hold区域，且终端半径0.981m仍在入口外开放空间。配置要求不超过0.12m/s峰值；下一次先用fresh snapshot的生产raw谓词检查起点body、连续body sweep和terminal hold，三者全free后才发planner-only`(0,+0.25,0)m`目标。unknown保持阻断，corridor内导航和N06原始出口仍未通过。
