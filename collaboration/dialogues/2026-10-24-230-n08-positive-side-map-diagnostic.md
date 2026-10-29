# N08.2t #230 任务摘要

- N08 remains active; #229 的 −π/2 单侧观察后 EGO 仍因 `planner_full_curve_unknown` 拒绝目标。N05 pre-action map 上 target terminal-hold 的 unknown 集中在 +Y 一侧，目标区域需从相机单侧视角再观察。
- #230 唯一物理变量为增加 +π/2 水平观察并回中，不加入 −π/2 水平侧视，沿用 #228 overhead 路线和全部门限。
- 同时增加只读 failure-map capture：goal 已匹配但 runner 未产出 spline 时仍抓取同 epoch/map snapshot，用于定位 action-time refusal。它不发布控制/目标，不改变实验动作。
- 只允许 DISARMED 支架扫描、fresh N05 gate、compute-only 与地图查询；stop envelope 未证明，XY 继续锁定。
- #230 运行后：19/19 支架阶段完成，fixture helper 定位错误保留；post-release/current-area N05 online/offline gate 同身份通过。806/806 LocalizationStatus valid，175/175 MapStatus ready。
- Compute-only 在 spline 前因 `planner_full_curve_unknown` 退出。新 observer 捕获到相同 goal/epoch/map 的失败后 raw snapshot，延迟 6.068 sim s。起点 body free、hold 有 309 unknown；目标 body free、terminal-hold 有 42 unknown；首个连续扫掠 query 有 6 unknown。没有 READY／XY／制动数据；已 landed/disarmed 且容器停止。
- 后续核对发现 N05 支架只有 x/z/yaw/pitch 轴，不具备所筛选的 +Y 释放平移；不改 spawn 或场景来绕过。改用同一释放点上的旧图候选目标 offset `[+0.10,+0.25,0] m`，路径和目标后 0.50 m corridor 查询均 free，但起点 hold 仍有 309 unknown。#231 只作 fresh N05 / compute-only 复核，旧图不授权执行，stop envelope 未证明前仍不做 XY。
- 证据：[报告](../../progress/evidence/n08-positive-side-map-diagnostic-20261024-230.md) 和 JSON。
