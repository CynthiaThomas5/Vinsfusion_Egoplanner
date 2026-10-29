# N10.3/#458 综合校准归档

- 对话摘要：[2026-10-28 #458 result](../../collaboration/dialogues/2026-10-28-458-n10-integrated-calibration-result.md)。
- 新增轻量 Markdown/JSON 结果报告，绑定既有 `artifacts/runs/n10-20261028-458-maxcnt220-integrated/` 原始输出；未修改运行原始文件。
- 明确总体 `INSUFFICIENT`：保留通过的正常导航/VIO/地图/source coverage/sensor/contact结果；运动 observer 零样本造成连续区间净空不足，tracking、资源容量依据和重规划标准未定。
- 源码追踪 PX4 `px4-rc.gzsim` 的直接 `PX4_GZ_MODELS/<model>/model.sdf` 路径，解释为什么 run-local wrapper 加入 `GZ_SIM_RESOURCE_PATH` 后仍未加载 root 模型 observer。
- 不补算正式次数、不转成 N15/N16 证据，不运行故障测试；N10 保持 `in_progress`。
- 验证：检查报告指标与归档 JSON；结构化报告可由 Python JSON parser 读取；`git diff --check` 待本轮最终统一执行。
- 后续：N10.3/#459 修复运行模型来源并做 no-flight SITL startup diagnostic。
