# #102 N06 连续15° yaw pilot

日期：2026-10-23。用户以`codex resume --last`恢复Goal完成模式，范围为N06；N06/S4及`next_goal=N06`不变。

## 约束

- 仅P0–P6单D435i仿真导航；本轮为未武装传感器夹具的Gazebo/VINS/EGO建图诊断。
- PX4、bridge、controller、setpoint、实机和flight保持关闭；unknown fail-closed、N05包络与预算、N06验收阈值不变。
- 保留所有既有worktree修改；本摘要不作为测试通过证据。

## 决定与结果

r27复用r26连续yaw运动及wall纹理surround，把名义转角由2°扩到15°。fixture truth达到14.731°，但sim62.404s以`normalized_cost_exceeded`关闭mapping gate；首条invalid status位于sim62.478s／truth约9.854°。MapStatus随后reset并未恢复；输入记录落盘，snapshot等待120s后超时，无snapshot或live EGO结果。详见[#102 evidence](../../progress/evidence/n06-continuous-yaw-15deg-observation-20261023-102.md)。

## 下一子项与待决项

下一步r28只改变传感器运动形式：同一wall／纹理surround内以已有慢速profile单轴X后退2.4m，再返回原点，零yaw／Y／Z。判据为健康和fresh identity持续到回程结束；若ready则取得三张匹配snapshot，检查body／hold sphere与planner-only live EGO。命令见[改动记录](../../progress/changes/2026-10-23-102-n06-continuous-yaw-15deg-pilot.md)。

N06仍缺两布局真实全机体连续曲线、安全hold、重规划handoff及故障拒绝矩阵；r27未建立正向入口。
