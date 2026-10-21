# 任务对话摘要

- 日期与任务 ID：2026-10-20，#057
- 用户目标与明确约束：继续完成单 D435i 仿真 P0–P6；保持旧来源只读、vendor 源码不原地修改、控制发布者边界不变；unknown、无效深度和视野外空间不得默认视为 free；保留现有工作树内容，不 stage、commit 或 push。
- 已确认的决定：继续对既有 EGO patch 0020 做隔离验证，不纳入 `dependencies/sources.json`；以 `0.5 m` 作为只覆盖名义方向不变球的 run-local 参数候选，不改项目默认 `0.099 m`。
- Agent 建议及待确认项：当前结果出现大量碰撞/rebound告警及中心线 inflation-mask 重叠；需要先查清这些告警与规划时地图状态的关系，再评估重复、多布局及进一步路线验证。没有待用户确认的执行项。
- 实施范围：固定 EGO revision 按15个 canonical patches重建，随后仅在临时源和独立 install overlay 中应用 patch 0020；复用 #305 墙体、箱体、圆柱和 `(2.5,1.4,1.0)` 目标，采集目标后与运动后地图快照，离线比较 spline 与 SDF/voxel。
- 发现与决定：五包隔离 build 通过；#306 捕获4条同 epoch B-spline，首条起始时间晚于最后一份快照0.910 s，且晚于运动开始。早期快照仍有unknown路径样本，最后快照采样为known/free，和等待更多观测相符但不能证明精确 planning-time 输入。SDF离线比较的名义球墙面余量仅0.3–33 mm；日志有6290条前三控制点障碍告警、3395条方向生成告警、583条终点障碍告警和一次内部急停/恢复。轨迹未执行；GOAL C保持pending。
- 后续只读源码审计：#306的6290条首段障碍告警全记录为`t=0`；`getInflateOccupancy`对unknown返回1、对地图外返回-1，优化器转为bool后两者都视为occupied。快照#03的四条最终样条首样点均known/free、未膨胀，但早于对应spline start约0.91秒。终点告警表示障碍控制点之后没有找到free控制点；方向告警表示未找到可用A*路径交点。另发现方向搜索循环可能在边界检查前访问越界向量元素，未确认是否在本次运行触发。详见`progress/evidence/p2-ego-planner-collision-warning-source-audit-20261020-306.json`。
- 对应改动记录：`progress/changes/2026-10-20-057-goal-c-unknown-policy-wall-probe.md`
