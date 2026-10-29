# N10.3/#384 到达驻留试验准备中止

**结论：无飞行准备失败，不计为飞行或校准样本。** 动态障碍注入观察器读取协议时缺少 `injection` 段并抛出 `KeyError`。没有创建目标文件/目标标记，也没有发送导航目标、enable 或控制样本。

PX4 原生状态话题直接读回 `arming_state=1`（disarmed）、`pre_flight_checks_pass=false`、`failsafe=false`；桥为 `DISABLED`、landed、未 armed、control disabled。复合探针因未收到任何 PX4 状态样本而把 `vehicle_remained_disarmed` 标为 false，不能覆盖原生话题读回。记录确认 `safe_to_stop_project_container=true`，该项目容器已安全停止。

机器报告：[JSON](n10-arrival-dwell-setup-abort-20261027-384.json)。源记录：`artifacts/runs/n10-20261027-384-arrival-dwell4/`。
