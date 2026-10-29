#396 N10 综合采集校准结果与离线分析修复

对话摘要：[2026-10-27 #396 综合采集校准结果](../../collaboration/dialogues/2026-10-27-396-n10-integrated-capture-result.md)

## 变更

- 归档并分层记录 #396：目标、保持与正常落地成功；离线验收仍 `INSUFFICIENT`；保留地图、净空、跟踪、资源和故障证据缺口。
- 新增 [校准结果报告](../evidence/n10-integrated-capture-result-20261027-396.md) 与配套 JSON，记录 run 身份、输入哈希和下一子项。
- 修复 `tools/debug_truth/evaluate_n10_replan_geometry.py` 在从子目录执行时找不到 `tools/evaluate_n08_curve_certificate.py` 的导入路径，并在 #396 归档上完成只读重算。

## 验证

- `docker run --rm --network none -v /home/huangxiaocheng/D435i-VINS-EGO-ROS2:/workspace:rw -w /workspace d435i-vins:dev python3 tools/debug_truth/evaluate_n10_replan_geometry.py artifacts/runs/n10-20261027-396-integrated-capture-calibration`：退出 0；输出首次点云 +3.588 s、首次正中心线净距 +3.944 s、首次超过机体水平扫掠半径 +4.348 s。快照 +1.016 s 仍全为 unknown；点查询服务不可用。
- 归档验收评估：14 项总体 `INSUFFICIENT`；飞行目标与正常安全末态成功。raw VIO RPE、速度误差和地图时龄仅在 provisional candidate 比较下 FAIL，候选门限没有变更。
- sensor capture evaluator：`PASS`；83,012 bag 消息、83,065 收据、单一 active identity，payload 内部缺失收据为 0。
- tracking/clearance 回放：7,999 配对，跟踪 P95 0.7066 m；静态场景离散 4 ms 净空下界 0.2283 m，平移-only 下界负值比例 25.28%。这不能证明连续运动或整个场景误差预算。
- 原综合 driver 退出码为 1，原因是归档分析读取旧到达字段失败、快照评估运行早于 sim-time 到达别名、tracking/clearance 运行早于动态 SDF 生成。上述是离线证据调度问题，不改变飞行结果；后续运行流程需按依赖排序。
- `git diff --check`、`python3 tools/project_status.py`：待最终写回后运行。

## 限制与下一步

#396 没有执行故障注入，不能证明深度超时、规划器退出等路径最终落地上锁。采样净空仍缺整个区间的受约束运动界；机体跟踪误差支持不足；障碍快照过早且 point-query 服务不可用；VINS 内部队列容量未知。下一项 #397 只改变规划器最大速度 `0.8→0.4 m/s`，并将 observer-only 地图快照移至障碍已出现在 raw 点云之后。任务失败时按原生正常降落路径和独立状态确认收尾，不复用一次性紧急 disarm 授权。
