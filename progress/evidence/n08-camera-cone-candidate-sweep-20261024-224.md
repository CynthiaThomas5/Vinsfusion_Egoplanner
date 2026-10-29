# N08.2n #224：从已通过 raw map 选择视场内制动候选

日期：2026-10-24。此项只是 #221 已通过同 epoch/map 的离线候选筛选；不构成新 run 准入或 N08 通过。

## 输入与方法

- 输入：[N08 #221 post-release map](n08-overhead-ceiling-isolated-20261024-221.json)，map id `a3940a23e72b445ba0f951c04f6fa0b9-f5272e80e3f440c1a0f28f26d5b00f94`，raw map SHA-256 `eb6aa6644ae21b82712f82e96ea0bbbccdd3e99b8edeefa6ef23952d1b5ea14d`。
- 起点由 #221 同图 `+Y0.6` 证书终点减去记录目标 offset 得到：`[0.1857077, -0.0651673, 1.0522347] m`。其机体球按原半径 0.730618 m 为 free；起点 0.980618 m terminal-hold 球仍有 41 unknown，原样保留。
- 通过 AST 从 [N06 production mirror](../../tools/probe_n06_live_layout.py) 调用既有 `raw_sphere_query` 和 `raw_line_sweep`，遍历 dx、dy ∈ [−1.0, +1.0]、0.1 m 网格。每个候选要求起点 body sphere、目标 body sphere、目标 terminal-hold 球和速度上限 0.15 m/s 下的整条 continuous body sweep 均 raw free；未填 unknown。
- 相机水平视场按 [D435i model](../../simulation/models/d435i/model.sdf) 的水平 FOV 1.518436 rad（87°）计算，并使用 #221 当前 yaw 0.026963 rad 检查候选方位。

## 筛选结果

网格中 40 个候选满足 raw body／终点 hold／完整直线 sweep 几何查询；其中 27 个方位在当前相机水平视场内。选择 offset `[+0.8, +0.3, 0] m`：

- 位移长度 0.8544 m，终点 `[0.985708, 0.234833, 1.052235] m`；相对相机光轴方位约 +19.01°，在 ±43.5° 视场内，边缘余量约 24.49°。
- 起点和终点 body 球分别 `2175/2175` free cells，无 unknown／occupied；终点 0.980618 m terminal-hold 球 `4919/4919` free cells。
- 生产 continuous-line mirror 查询 35 次全部 free，覆盖半径 0.742824 m，无 unknown／occupied。候选速度上限保持 0.15 m/s。
- 纯 +Y0.4 m 虽有 raw 几何证书，但方位约 +88.46°，超出当前相机 FOV，故不作为实际执行方向。

保留的起点 terminal-hold unknown 不属于这条从已建立 stationary hold 出发的 forward curve 查询；#212 固定 hold baseline 和 N07 悬停通过项均保留。之后每个新 run 仍必须重做 fresh N05 current-area gate、同图 body／curve／终点 hold 查询及 EGO live full-curve 认证。该报告不能单独授权 XY。

## 下一步

新增 `n08_compute_only_camera_cone_goal.json`，在同一 N08 顶板＋box/column 场景、使用 #221 已完整完成的 `n08_overhead_free_sector_view` 采集路径重新启动。fresh raw map 若仍满足上述查询，先运行 bridge-input-isolated compute-only，检查 READY／取消／hold／landing；此项不执行 XY。实际运动需在同 run 确认全曲线和保守 stop boundary 后再开始。

复核来源：

- raw map：`artifacts/runs/n08-20261024-221-overhead-ceiling-isolated-01/n05-post-release/n05-live-raw-map.npz`
- post-release gate：`artifacts/runs/n08-20261024-221-overhead-ceiling-isolated-01/n05-post-release/n05-live-entry-check.json`
- report JSON：[`n08-camera-cone-candidate-sweep-20261024-224.json`](n08-camera-cone-candidate-sweep-20261024-224.json)
