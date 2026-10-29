# #407 N10 地图体素归因

对 #404 raw map snapshot 新增离线逐格几何/证据来源审查工具和边界几何单测。分析复现 18 个箱体内完整 raw-free 体素，确认 3×7×1 聚集；完整 MCAP 无深度话题，稀疏图像和 mapper 源码均不能恢复逐格更新因果关系。故归因结论为不足，保留 raw 分类候选 FAIL，不修改运行策略或验收门限。

- 新增 `tools/debug_truth/analyze_n10_occluded_free_cells.py`、`tools/test_n10_occluded_free_cell_attribution.py`。
- 证据：`progress/evidence/n10-map-cell-attribution-20261028-407.md/.json`；原始离线报告及输入 hash 在 `artifacts/runs/n10-20261028-407-map-cell-attribution/voxel-source-audit.json`。
- 验证：py_compile、2 项 unittest、离线归档分析通过。
- 局限：没有完整 depth 或逐体素更新时间；不能归咎于旧 free 投票或当前 mapper 缺陷。下一次既定综合校准追加目标 ROI 深度及目标栅格前后状态。N10 仍 in_progress。
- 对话摘要：`collaboration/dialogues/2026-10-28-407-n10-map-cell-attribution.md`。
