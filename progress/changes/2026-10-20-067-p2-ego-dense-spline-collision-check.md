# GOAL C B-spline 密集 inflation 检查候选 #318

对话摘要：[2026-10-20-067](../../collaboration/dialogues/2026-10-20-067-p2-ego-dense-spline-collision-check.md)

新增 `dependencies/patches/ego/0029-dense-spline-inflation-check-experiment.patch`，叠加在 #315 隔离源码/patch 0028 后。它在最终曲线保存前按10 ms采样 first-two-thirds 安全窗，并把 GridMap非零结果（图外、unknown、inflated）作为阻塞返回失败。patch SHA-256记录在[报告](../../progress/evidence/p2-ego-dense-spline-collision-check-20261020-318.json)；`git apply --check`通过，应用后与独立候选源文件精确一致；未修改vendor/canonical依赖。

验证：`bash artifacts/runs/p2-ego-dense-spline-collision-check-20261020-318/build-and-test-container.sh`（五包Release构建，A* endpoint用例4/4）；`bash artifacts/runs/p2-ego-dense-spline-collision-check-20261020-318/run-container.sh`（planner-only目标探针）。运行日志记录3次最终曲线阻塞拒绝，三处均unknown/inflated；随后探针收到1条未执行 spline。无PX4、controller、trajectory server、truth或control topic。使用同一binary的 #319 后续捕获一条样条start_time同刻快照并作离线10 ms对照。

限制：只有一个候选patch、单场景少量运行；力驱动传感器轨迹不是确定性回放。Inflation voxel不是实际碰撞测量，中心线未扫掠机体，也无地图完整度/精度或tracking误差。补丁仍是experimental，GOAL C/D/F和阶段状态不变。
