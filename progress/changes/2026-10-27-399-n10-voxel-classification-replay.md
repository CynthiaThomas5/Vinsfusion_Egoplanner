# N10.3/#399 体素体积分类与验收器复算

对话摘要：[N10.3/#399 复算](../../collaboration/dialogues/2026-10-27-399-n10-voxel-classification-replay.md)。

更新了 `tools/debug_truth/evaluate_n10_occupancy_snapshot.py`，在离线快照报告中逐个检查箱体内 voxel 的八角变换位置，区分完全位于实体箱体的体素与跨表面的体素。已存在的只读 point archive 不再被重新打开写入；增加 `--output` 以便保留原分析并生成版本化报告。

更新了 `tools/debug_truth/evaluate_n10_acceptance.py`：允许显式绑定版本化 snapshot report；没有分区字段时继续 `INSUFFICIENT`，有八角几何分区时只把完全落在实体箱体中的 known-free voxel 计入 truth-occluded 候选，不再把所有 center-inside free voxel 推断成 occluded。逻辑只在离线评估中使用，不发布控制或新增运行门。

#398 快照中 center-inside `known_free=34`，其中 13 个 cell 八角全在实体箱内、21 个跨边界。草案阈值为 0 时，raw classification 离线候选指标为 `FAIL`；其余验收指标整体仍 `INSUFFICIENT`，因为阈值仍是 draft，surface 只有两面有支持、tracking/净空标准、故障末态和资源容量依据未完成。latest depth source stamp 晚于第一条被记录 box cloud 604 ms、早于快照前第二条被记录 cloud 16 ms；cloud 每十帧采样，精确融合帧未关联。细节见[报告](../evidence/n10-voxel-cell-classification-replay-20261027-399.md)。

验证：

- `PYTHONPYCACHEPREFIX=/tmp/n10-399-pycache python3 -m unittest tools.test_n10_occupancy_snapshot tools.test_n10_acceptance`：29 项通过。
- `python3 -m py_compile tools/debug_truth/evaluate_n10_occupancy_snapshot.py tools/debug_truth/evaluate_n10_acceptance.py`：通过。
- 两份 evaluator 重放 #398 并输出版本化 JSON；总评 `INSUFFICIENT`，无运行时副作用。
- `git diff --check`：通过。

下一项：修正 run-local 快照触发顺序，使 source stamp 覆盖首个被记录的箱体 cloud 后再抓快照；同时审计一类缺少当前版本端到端依据的故障到 PX4 landed/disarmed 路径。N10 保持 `in_progress`。
