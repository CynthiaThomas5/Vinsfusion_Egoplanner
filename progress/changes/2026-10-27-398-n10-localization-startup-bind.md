# N10.3/#398：修复定位流首次发布者绑定竞态

对话摘要：[2026-10-27 #398 定位启动绑定修复与综合校准重试](../../collaboration/dialogues/2026-10-27-398-n10-localization-startup-bind.md)

## 变更

- #397 的 EGO 速度校准在起飞前因 PX4 `px4_local_position_invalid` 结束。adapter 日志显示 `propagated_publisher_missing_or_changed`，但当时 propagated 流还没有首条消息及绑定 GID；VINS 已完成初始化，健康代价约 0.097。该启动次序被误判为流身份变化。
- `uav_localization` 对尚未由首条消息绑定的流跳过定时 endpoint 检查。消息回调仍要求唯一 DDS publisher，并绑定其 GID 与 ROS 节点；绑定后，publisher 消失、多 publisher、GID 变化或 VINS 节点变化仍锁存完整性故障。
- 新增纯函数覆盖未绑定、相同身份、GID 变化和节点变化四种情况。
- 为修复后综合校准准备 #398，保持 EGO `max_velocity=0.4 m/s`、其余校准配置和观测方案不变；此次代码修复会体现在新运行身份，不复用 #397 身份。

## 验证

- `python3 tools/test_localization_health.py`：8 项通过。
- `PYTHONPYCACHEPREFIX=/tmp/n10-398-pycache python3 -m py_compile ...`：源码和定向测试语法检查通过。
- `bash tools/project.sh build ros`：17 个 ROS 包构建通过。
- `git diff --check`：通过。
- #397 原始预检归档判定没有 goal、未武装、PX4 本地位置无效且外部视觉未融合；独立收尾读回确认 landed/disarmed、bridge DISABLED、控制设定点为零，项目运行容器已停止。详情见[证据报告](../evidence/n10-localization-startup-binding-20261027-398.md)。

## 状态

#397 不计作 0.4 m/s 校准飞行。#398 综合校准已准备，需在新 runtime identity 下完成并由独立评估器复核；N10、N10.3 均保持未通过。
