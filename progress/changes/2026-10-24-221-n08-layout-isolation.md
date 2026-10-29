# N08.2k #221：让顶板成为唯一场景变量

- 修正 #220 首次布局隔离缺口：N08 专用 `n08_overhead_calibration` 明确引用 `wall_box_column` 为 `base_layout_id`，N05 runner 从唯一 N04 几何源读取既有 box/column，再叠加 N08 顶板。未复制或改写 N04 对象定义。
- N05 scene manifest 记录 layout config 与 base layout config 的相对路径和 SHA256，`n05-run-inputs.json` 同时包含两份配置哈希。
- 唯一环境变量相对 #218 为真实 8×8×0.1m 顶板；复用 #218 的 N05 扫描姿态、路线、阈值、地图策略与 EGO 半径。
- 验收：运行时生成的场景须含 baseline 2 个障碍与顶板；同 run N05 release gate online/offline 一致；raw map 对顶板为 occupied、候选净空 sphere/曲线全 free。未全部通过，不启动 compute-only 或 XY。
- 产物：`progress/evidence/n08-overhead-ceiling-isolated-20261024-221.{md,json}`、run `artifacts/runs/n08-20261024-221-overhead-ceiling-isolated-01/`。

## 运行结果

- #221 的 N08 layout 复用了 N04 `wall_box_column` 与新增顶板；scene manifest 记录两个 config 来源和哈希。support scan 15/15；helper 的 localization validity 错误保留，但 after/post-release N05 online/offline gate 均通过，identity 稳定，容器安全停止。
- 顶板附近 raw occupied ROI 有 1,176 voxels。same-map EGO body sphere start 与 +Y0.6 goal 均全 free；terminal-hold spheres 分别有 41／16 unknown，候选 line 仅在终点 hold-neighborhood 失败。compute-only withheld，无 XY/braking data。
- 下一子项 #222 用固定高度 yaw ±π/2、pitch0 水平观察已识别的后方／目标前方 unknown cells。报告见 [#221 evidence](../evidence/n08-overhead-ceiling-isolated-20261024-221.md)。
