# 2026-10-27 #398 定位启动绑定修复与综合校准重试

## 任务

继续用户明确授权的 Goal 完成模式 N10.1–N10.7。#396 的综合校准总评为 `INSUFFICIENT`；#397 只改 EGO `max_velocity` 为 0.4 m/s 的重试在 PX4 原生预检阶段停止，尚未提交目标或武装。用户已授权的一次紧急 disarm 在 #391 消耗，不再复用。

## 当前决定

- #397 的日志支持定位 adapter 启动绑定竞态：VINS 在 8.548 s 完成初始化；optimized 与 telemetry 已配对，normalized cost 为 0.097；此时 propagated DDS 发布端点已出现、但 adapter 尚无 propagated 消息/GID。定时身份核对把空 GID 判为 publisher changed，造成 PX4 本地位置有效性及 EV 融合均未建立。
- 修复为：尚未收到首条消息的流不做 endpoint 身份轮询；首条消息在回调内按原逻辑要求唯一 publisher 并绑定 GID/节点；后续任何 endpoint 缺失或身份变化仍锁存。未新增等待、健康、质量、速度、记录器或验收门。
- #398 保持 planner `max_velocity=0.4 m/s`、其余 profile、spawn 和诊断时长不变，用于确认修复后完整传感器/定位链、PX4 EV 融合及跟踪/净空校准。
- 先单测与 17 包 ROS 构建，再运行新鲜 runtime identity 的综合校准。#397 保留为安全的预检失败，不计飞行结果。

## 约束

- #381–#396 有效档案继续按同身份和适用范围复用，不倒算 N15/N16 正式次数。
- 评估器和记录器只读，不因 CPU、队列、统计值或缺数据改变飞行决策；PX4 原生预检、EV 融合、EGO watchdog 和已实现的安全故障处理保持有效。
- #398 正常落地上锁并独立读回后停止项目栈；不再次使用紧急 disarm。

## 产物

- 启动绑定修复、定向测试及构建记录：[change record](../../progress/changes/2026-10-27-398-n10-localization-startup-bind.md)
- #397 故障证据与 #398 重试状态：[evidence report](../../progress/evidence/n10-localization-startup-binding-20261027-398.md)
