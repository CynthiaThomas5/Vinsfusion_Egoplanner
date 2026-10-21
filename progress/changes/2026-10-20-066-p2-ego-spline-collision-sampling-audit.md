# GOAL C B-spline 碰撞采样静态审计 #317

对话摘要：[2026-10-20-066](../../collaboration/dialogues/2026-10-20-066-p2-ego-spline-collision-sampling-audit.md)

本轮新增同快照离线分析脚本 `artifacts/runs/p2-ego-spline-collision-sampling-audit-20261020-317/audit_collision_sampling.py` 与 JSON 输出。脚本从 #316 serialized B-spline 重建曲线，对比 EGO optimizer 的 endpoint-distance 自适应步长与 10 ms 网格，并使用各轨迹配对快照查询 inflation mask。

结果：优化器复现步长为0.189/0.189/0.337 s，采样点均未命中配对快照中的 inflation mask；10 ms前2/3检查在轨迹2发现10点（1.15–1.24 s），轨迹3发现6点（1.20–1.25 s）。对应控制点检查无命中。审计只重现同快照采样差异，不证明当时在线地图字节一致、真实碰撞或运行安全。

验证：`python3 artifacts/runs/p2-ego-spline-collision-sampling-audit-20261020-317/audit_collision_sampling.py`（`SAMPLING_GAP_REPRODUCED`）；输入快照及输出 SHA-256 记录在[报告](../../progress/evidence/p2-ego-spline-collision-sampling-audit-20261020-317.json)。未运行构建或仿真。GOAL C/D/F不改变状态；下一步建立隔离的10 ms trajectory validation候选。
