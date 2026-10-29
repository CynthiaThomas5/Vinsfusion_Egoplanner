# #202 变更记录：N07 右图像输入健康门拒绝起飞

## 范围

Goal 完成模式，用户指定 N07。子任务 N07.48 #202：固定配置和门限下做下一次独立 cold start。仅写入 run-local graph observer copy 和运行进度证据；没有修改源码、配置、健康门或验收阈值。

## 结果

N05 initial gate fail-closed 后，经 12/12 支架路线、summary 14/14、fresh post-release/current-area online/offline gates 成功取得地面准入证据；fixture helper health 错误保留。Hover runner 起飞前因 `LocalizationStatus=right_stale`、bridge `localization_not_tracking` 失败，没有 goal 或起飞；streak 保持 0/3。仿真时钟无倒退，VINS raw odom/solver、depth 和 occupancy 继续更新；优化定位输出停留在约 sim461.2s，右图像输入 stale 的具体来源未保存。

## 验证

- `N07_KEEP_SIM=1 bash /tmp/n07-192-n05-runner.sh n07-20261024-202-01 wall_box_column n06_full_airframe_retreat_240_oblique_separated_return`：路线 12/12、summary 14/14；helper 错误保留。
- current-area `check_n05_entry_live.py` + `evaluate_n05_entry.py`：online/offline fresh gate 接受且匹配。
- `tools/audit_px4_boot.py .../n07-20261024-202-01`：PASS。
- `tools/run_vio_no_goal_hover.py ...`：FAIL_PRECONDITION，`vio_bridge_map_preconditions_not_ready`，reason `right_stale`；无 goal。
- 独立 preflight/final safety readback 11/11；`bash tools/project.sh stop n07-20261024-202-01`：exit 0，容器 `exited 0`，无活动项目容器。
- 本记录写回后复验 `python3 tools/project_status.py` 和 `git diff --check`。

## 限制与下一步

未取得 ACTIVE/armed graph、30秒 hover、hover evaluator 或 airborne ULog 证据。`right_stale` 的右图像源时间／投递细节未记录；保留健康门不变，继续 #203。详见 [N07 #202 报告](../evidence/n07-preflight-right-stale-20261024-202.md) 与 [对话摘要](../../collaboration/dialogues/2026-10-24-202-n07-preflight-right-stale.md)。
