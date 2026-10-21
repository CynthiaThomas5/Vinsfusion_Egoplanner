# P5 VINS 质量门窗口变化复核

## 改动

- 扩展 `tools/evaluate_vio_quality_alignment.py`：在首个 health gate 旁报告前一条代价样本、代价/残差维数/视觉观测数变化、首次回落到阈值内的样本，以及后续2秒内峰值和越线样本数。
- 增加覆盖短暂恢复和后续再越线的测试。
- 新增 [#175–#178 质量门动态复核证据](../evidence/p5-vio-quality-gate-dynamics-20261019-175-178.json)，哈希关联四轮原始 VINS 遥测、真值、位姿、PX4飞行报告及计算源。

## 结果

- 四轮首个门控的 normalized_cost 为1.0260–1.1965，紧邻前一求解样本为0.3595–0.5574；final_cost 增加832.47–1074.46，残差维数增加68–112，`visual_observations` 增加20–32。
- 首次门控时的固定 SE(3) 对齐位置误差仅0.0110–0.0245 m。下一条遥测在0.064–0.132仿真秒内回落到1.0以内，但每轮门控后2秒窗口内仍有7–14条越线样本。该后续窗口已包含控制器取消目标并降落的响应，不能当作原目标的无干预延续。
- 四轮首次位置误差超过0.30 m发生在所配对质量遥测戳后2.508–4.028秒。短试验既不能证明首次尖峰是误报，也不能证明1.0是已校准的预测阈值。
- `max_normalized_cost=1.0` 未修改，定位仍按现有逻辑在 TRACKING 期间质量失败后锁定。P5 继续进行，GOAL A–H 未完成。

## 验证

- `python3 tools/evaluate_vio_quality_alignment.py --capture <run>/vio-truth-capture --flight-report <run>/vio-ego-flight-report.json --output /tmp/p5-vio-quality-analysis-<run>.json`：对 #175、#176、#177、#178 均 PASS。
- `python3 tools/test_vio_quality_alignment.py`：3 tests PASS。
- `python3 -m py_compile tools/evaluate_vio_quality_alignment.py tools/test_vio_quality_alignment.py`：PASS。
- `python3 tools/project_status.py`：PASS，仅结构检查。
- `git diff --check`：PASS。

## 局限与下一步

遥测只有聚合 Ceres `final_cost` 和残差维数，未分解视觉、IMU、边缘化先验代价，也未保存逐帧图像或足够的特征残差。因此同时增加的视觉观测计数只是窗口更新线索，不足以归因。下一步在 run-local VINS 诊断副本中采集分组代价及特征/图像时间，再用相同质量门比较悬停与目标运动；不旁路健康门，不把真值接入导航或控制。

## 对话摘要

[P5 VINS 质量门窗口变化复核](../../collaboration/dialogues/2026-10-19-063-p5-quality-gate-dynamics.md)
