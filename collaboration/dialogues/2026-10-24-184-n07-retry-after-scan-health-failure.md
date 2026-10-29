# N07 #184 对话摘要：支架扫描返回段代价尖峰

## 约束

- 继续已授权的N07 Goal完成范围，N07仍需三次连续合格冷启动。
- 地下空间不作为可飞区域；不放宽定位健康门或N05门限。
- 定位／准入拒绝时禁止起飞，先安全detach、独立读回和停容器。

## 结果与判读

#184使用和#183相同的固定组合、新cold-start epoch。支架扫描在返回段第7/12阶段因`normalized_cost_exceeded`失败，未生成ready marker或飞行。原始VINS telemetry捕获到source 328.252s的一帧代价尖峰，按当前健康公式复算为1.969642，与helper记录完全一致；后续代价回落不取消fail-closed。夹具确认已移除，PX4 DISARMED且落地，容器退出0。连续计数保持0/3。

失败报告见[证据](../../progress/evidence/n07-preflight-localization-failure-20261024-184.md)，执行记录见[变更记录](../../progress/changes/2026-10-24-184-n07-retry-after-scan-health-failure.md)。下一子项#185使用新cold start继续；门限不变。
