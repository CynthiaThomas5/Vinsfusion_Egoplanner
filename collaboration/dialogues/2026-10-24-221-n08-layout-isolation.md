# 对话摘要：N08 #221 隔离真实顶板变量

- #220 在 N05 第 6/15 阶段因 normalized_cost_exceeded 结束，没有 release map。复核发现首次 N08 layout 仅含 ceiling，遗漏 wall_box_column 的 n04_box/column，因此不能将运行失败归因于 ceiling。
- #221 使用唯一来源 `n04_geometry_layouts.json` 的 wall_box_column 为 base，N08 runner 合并其 box/column 与 `n08_overhead_calibration.json` 中的真实 ceiling；manifest 保存两份配置哈希，不复制几何定义。
- 相对 #218 支架流程唯一改变为加顶板；N05/N06/EGO 参数和 unknown fail-closed 规则不动。
- 只在同 run N05 gate、顶板 raw occupied、start/goal/curve spheres 全 free 时继续 bridge-isolated compute-only。没有停止边界前不执行 XY。

## 实际结果（补充）

- 15/15 N05 支架阶段完成，helper localization error 保留；fresh after 与 post-release gates online/offline 均通过、same epoch/map，PX4 landed/DISARMED、fixture removed。
- N08 顶板在 raw occupancy 里形成 1,176 个 occupied voxel（只作 footprint ROI 统计）。起点与 +Y0.6 目标 body spheres 全 free。
- 0.25 m terminal hold 扩展后，起点 41、目标 16 unknown；straight-line candidate 只在终端 hold query 被拒。compute-only withheld，无 XY 或 brake evidence。
- #222 下一步 yaw ±90° 水平观察对应 y≈−1.05 和 y=1.25–1.45 的未知扇区。
