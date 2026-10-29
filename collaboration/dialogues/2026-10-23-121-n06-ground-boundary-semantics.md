# #121 N06.4 ground boundary semantics

- 用户指出地下区域不属于飞行空间，要求继续处理 N05 因地下 unknown 拒绝的问题。
- 依据 #145 raw map，38 个接触体积 unknown 位于地面 voxel slab 以下。将空间策略解释为只检查物理可飞行体积：PX4 确认 landed 且 fresh raw-ground plane 有效时，在起降垂直阶段只排除整格位于保守地面下界以下的 cells。
- 地面边界采用 fitted plane、95th percentile 拟合残差、plane 跨 voxel XY cell 的最大坡度变化和半个地面 voxel 厚度；只有 cell 上表面到达或低于保守下界才排除。与边界相交或位于其上、HOLD 阶段、地面未确认、地图过期或越界时，unknown 仍按原规则拒绝。不得合成 free rays 或改不确定度 margin。
- 实施后先跑几何/N05/profile 定向测试并对 #145 archived raw map 作当前策略离线重放。只有该 replay 与 fresh live online/offline gate 一致且正向，再复核两个布局的受影响 N05/N06 planner 出口。全程保持 DISARMED、bridge DISABLED、无控制/goal、不执行规划曲线。

## 完成结果

- #145 archived raw map 按新规则离线重放接受全部入口阶段；其历史 live check 仍是旧规则下的拒绝，故该历史报告不声称 online/offline 匹配。
- #146 wall 与 #148 corridor 全机支架扫描各 12/12 阶段。支架释放后 fresh N05 online/offline 五阶段 gate 均 `accepted=true`，结果一致；PX4 DISARMED、bridge DISABLED、无控制、goal 或真值输入，epoch/map_id 稳定。
- #151 wall 当前 N06 probe 的三快照、live body/sweep/hold 和两个目标 handoff 均通过；#123 corridor planner 证书的 EGO/plan_env、补丁和有效安全半径与当前版本一致。#152/#153 因 VINS health gate 关闭而未提交目标，作为负向诊断保留。
- 两个 N05 fixture helper 都记录失败字符串，虽然 12/12 阶段和 post-release gate 完成、最终 localization valid；corridor remove acknowledgement 也缺失但模型列表确认 fixture 不存在。警告保留于验收报告，不把实验解读为飞行或全流程运行通过。
- N06 标记 `passed`（planner integration scope），`next_goal=N07`；N07 保持 `not_started`。没有起飞、飞行或执行 planner 曲线；N08 制动测量及整个 GOAL 的 P6/S4、A–H 仍未完成。

证据与哈希：[N06.4 / N06 完成证据](../../progress/evidence/n06-ground-boundary-release-admission-20261023-121.md)。过程与验证命令：[改动记录](../../progress/changes/2026-10-23-121-n06-ground-boundary-semantics.md)。
