# GOAL C B-spline 密集 inflation 检查候选 #318

基于 #315 的隔离 EGO 源树，在 `reboundReplan` 完成 optimize/refine 后、`updateTrajInfo` 前，新增10 ms间隔的最终曲线检查，范围沿用现有 first-two-thirds 安全窗。`getInflateOccupancy` 返回非零（含图外、unknown、inflated）则拒绝候选，保留其余FSM行为。新增补丁0029只放 `dependencies/patches/ego`，不更改 canonical sources 或 `src/vendor`。

补丁应用检查通过，独立源码重放与候选 `planner_manager.cpp` 逐字节一致。五个 Jazzy Release 包构建通过，GridMap/AStar endpoint测试4/4通过。planner-only运行中出现3次 `final_spline_collision_reject`，样点均为 map内 unknown（`raw=0`, `inflated=1`）；随后探针收到1条 B-spline。没有controller、trajectory server、PX4、真值或控制topic，样条未执行。

这说明候选分支的检查会拒绝被发现阻塞的最终样条；单轮没有检查成功发布曲线的同步地图，所以使用同binary在独立epoch做 #319 快照验证。#319有一条接受曲线的10 ms中心线全程未命中已知inflation/raw occupied/unknown格。地图known覆盖低、没有机体扫掠、跟踪误差或真值，仍是诊断，不是安全通过；patch保持隔离。
