# N10.3/#395 综合采集准备更新

对话摘要：[用户约束与决定](../../collaboration/dialogues/2026-10-27-395-n10-integrated-capture-preparation.md)。

## 改动

- 完成只读左右目/IMU payload 与 source-receipt 记录、有限队列和容量报告；正常 SIGTERM 关闭 rosbag 后再收尾观察器。
- 增加离线 payload/receipt/身份评估器；零飞行 smoke 可校验 transport，但与任务评估明确分开。
- 修正 point-query 的任务身份解析和冲突检查，允许在 flight record 写出前由明确的 query spec 绑定 goal。
- 增加 #395 烟测 JSON/Markdown 证据。两次先行关闭失败保留于运行归档；最终 smoke 通过，不生成飞行资格。

## 验证

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tools.test_n10_acceptance tools.test_n10_clearance tools.test_n10_sensor_capture tools.test_observer_window tools.test_n10_map_query_contract`：48 passed。
- 相关 Python `py_compile`、`bash -n`、`python3 tools/project_status.py`、`git diff --check` 均通过。结构检查不代表构建或 SITL 通过。
- 最终 smoke: capture evaluator `PASS`; 9,995 MCAP payloads 均有 source stamp/frame 收据；内部 payload/receipt mismatch 为零；bag exit 0。PX4 保持未武装，bridge DISABLED，控制样本为零，无任务开始。

## 局限与恢复

VINS 内部队列容量仍未知。零飞行 smoke 未验证任务期 map query、物理步级净空、重规划、长时资源和原生故障终态。#395 仅关闭采集准备子项，N10 父目标继续 `in_progress`。run-local #396 已准备完整身份 query injector、prelaunch freeze 和安全终止读回协议；唯一场景变量为诊断 ACTIVE hold 从60缩短至15仿真秒。当前尚未启动 stack 或任务。后续观察器结果只进入离线证据；任务结束后必须独立确认 native landed/disarmed 再停止项目会话。一次性紧急 disarm 授权已用于 #391，后续不复用该授权。
