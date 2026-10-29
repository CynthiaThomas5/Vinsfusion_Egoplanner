# 2026-10-23 #100 N06 motion-transient diagnostic

对话摘要：[N06 motion-transient diagnostic](../../collaboration/dialogues/2026-10-23-100-n06-motion-transient-diagnostic.md)

## 结果与记录

- r25 将0.25°分段步进的角加速度降低四倍，但在truth yaw约0.927°的gate event仍锁存`normalized_cost_exceeded`；首条invalid状态在truth yaw约0.938°。
- 锁存LocalizationStatus在health limit 1.0上仅超至1.04236；来源stamp约sim34.012s，`good_pairs=504`。IMU积分与debug truth几乎一致，VINS估计约偏高0.705°。MapStatus不恢复，snapshot-01在120秒readiness timeout后无输出。
- input recorder和motion truth均完整保存；容器及匹配进程已停止。host exec session结束时没有保留runner exit code；snapshot日志含明确120秒TimeoutError。
- 新增 [机器报告](../evidence/n06-yaw-motion-transient-20261023-100.json)、[证据报告](../evidence/n06-yaw-motion-transient-20261023-100.md) 与 `n06_yaw_continuous_2deg_quarter_accel_pilot.json`。
- r26保持r25角加速度、峰值、2°命令总角和场景，只把8次起停改为一次加速、连续匀速、一次减速；尚未运行。
- CURRENT、GOAL、execution plan、milestones及N06主报告更新为r26唯一当前子项；N06/S4与原出口保持`in_progress`。

## 验证

- r25 runner：motion和input recorder完成；snapshot readiness 120秒失败，原因`map_reset_acknowledged`。项目容器和匹配进程停止。
- r26 profile复算：一次加速／七个匀速／一次减速，8个0.25°等效相位合计2°；角加速度`0.0026179939 rad/s²`、峰值速率`0.00337982 rad/s`，初始静置5秒、末端静置5.164秒。
- 写回后运行`python3 tools/project_status.py`、profile/static consistency check、`git diff --check`和`git status --short --branch`。结构检查不代替build、SITL或N06正向出口。

## 限制与下一步

不能将r25 post-lock telemetry外推成首次失效根因；r25在首次失效时的锁存normalized cost来自LocalizationStatus，其他分项没有完整历史记录。下一步只验证连续转向是否比反复rest-to-rest更能保持健康和fresh map。保持所有N06出口及unknown拒绝不变。
