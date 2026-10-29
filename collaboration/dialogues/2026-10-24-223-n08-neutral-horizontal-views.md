# 对话摘要：N08 #223 水平观察分段回中

- N08 仍是完整目标，#212 hold baseline 保留，不复测；N07 已通过项不复测。
- #222 的新 profile 在连续 yaw −π/2→+π/2 期间触发 `normalized_cost_exceeded`，1.00967 超过原固定上限 1.0。它未到同 run N05 post-release gate，不能据此判断 raw unknown 是否清除。
- #223 假设完整 180°转动导致 VINS 特征／估计退化，但因果尚未证明。仅把方向切换改为左视角→yaw=0 停留→右视角，并保持 N05/EGO 门限、未知策略、物理布局及支架路径不变。
- 若定位和 fresh N05 gates 全通过，再以同 epoch/map 离线复算全身及停止保持查询；否则不启动 compute-only／XY。实际制动仍未开始。

## #223 结果

- 左视角和 yaw=0 回中完成；cost 到回中停留末尾已升至0.979。开始右转时 health cost 越过固定 1.0 门限至1.00292，run fail-closed；N05 post-release gate 未开始，未得到地图查询结果。
- 这排除了“仅需避免一次连续 180°扫动”这一简单解释，但不能区分累计转动、视觉场景或其他估计退化原因。没有理由放宽 health 门限。
- 已 landed/disarmed、fixture removed、容器退出0。完整记录：[报告](../../progress/evidence/n08-neutral-horizontal-views-20261024-223.md)。
- 下一步先复用 #221 同图 raw map 离线筛选相机视场内、已知 free 的目标方向，再为新运行重建 fresh N05 gate。
