# N08 #327 正式出口完成审计与进度交接

对话摘要：[最终审计](../../collaboration/dialogues/2026-10-26-327-n08-completion-audit.md)。机器聚合报告：[N08 final audit](../evidence/n08-final-completion-20261026-327.md)。

## 改动

- 新增 #325 单次运行证据报告与 JSON，记录第三次普通单程 `terminal_stop`、N05/N06 admission、3 秒保持、降落、独立读回和 PX4 ULog 末态。
- 新增 #326 近峰值 caller-cancel 补测的前置拒绝报告。N05 fresh 接触体积仍含 51 个 raw-unknown cell；同身份在线／离线一致拒绝，故没有目标、解锁或飞行。保存独立 unknown-volume 审计。
- 新增 #327 N08 三次正常运行、hold/compute/execute 对照、#321 caller-cancel 及预算消费的机器与 Markdown 聚合报告。
- 更新 N08 测试计划的执行结尾、`progress/CURRENT.md`、`progress/milestones.json`；N08 正式状态置为 `passed`，下一依赖满足项设为 N09。N09 不在本轮启动。
- 本轮没有修改运行时代码、配置、速度门限、包络或返航语义。

## 验证与结果

- #322、#324、#325：同 runtime-contract `75aaa541...`，3 个独立 epoch/map_id；native action PASS、独立 evaluator 全检查 PASS、N05/N06 capsule、停止保持和目标区降落 PASS。
- #325 ULog 使用 `pyulog 1.3.0` 只读解析：752 个 `vehicle_status` 样本最后 `arming_state=1`，418 个 `vehicle_land_detected` 样本最后 `landed=true`；独立 6 秒读回 `LANDED`、控制 disabled、控制消息计数 0。
- #321：caller-cancel → 已认证替代停止样条 → 实际停车／3 秒保持 → 终点降落通过，取消距离 0.30407 m，单独于三次正常到达。
- #296 的 0.50 m caller-cancel 候选已进入实际 pre-enable／airborne raw-map corridor 和 evaluator。N05 机体清距、空间不确定度和 tracking margins 未增大；正常终点停止由整条已认证曲线和 hold 区域覆盖。
- #326：同身份 N05 online/offline 以 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope` 拒绝；40 秒只读 preflight 本身通过；no goal/enable/flight，container 以 exit 0 安全停止。该建议速度窗口仍无测量，不计入 N08 正式三次目标统计。
- 生成/复核命令：`PYTHONPATH=tools python3 tools/debug_truth/audit_n05_unknown_volume.py --live-report artifacts/runs/n08-cancel-peak-prescan-20261026-326/n05-current-area/n05-live-entry-check.json --output progress/evidence/n08-cancel-peak-n05-unknown-volume-20261026-326.json`；结构化报告 JSON 在收尾时用 `python3 -m json.tool` 校验，项目状态用 `python3 tools/project_status.py` 检查；最终执行 `git diff --check` 并查看 `git status --short --branch`。

## 局限与下一步

- 本结论仅是当前仿真候选版本的 N08 正式出口，不是实机或普适制动保证。观察到的减速度 p10 不是已保证的下界；0.50 m 仅适用于当前低速前向取消候选协议。
- 详细测试计划 D.6 建议的近峰值取消触发补测被 fresh N05 安全门拒绝。没有调低门限或绕过门禁；这项速度点需在以后取得合法 known-free 接触体积后另行测量。
- `project.sh mission` 在合格运行里仍会因 matplotlib 缺失导致可选绘图步骤返回 1；native flight 和独立无图 evaluator 通过。N07 未复测。
- N09 是 `next_goal`，本轮未开始。
