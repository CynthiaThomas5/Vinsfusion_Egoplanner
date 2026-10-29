# 2026-10-23 #101 N06 continuous yaw pilot

对话摘要：[N06 continuous yaw pilot](../../collaboration/dialogues/2026-10-23-101-n06-continuous-yaw-pilot.md)

## 结果与记录

- r26以连续加速／匀速／减速执行2°名义yaw，truth实际2.0116°。Recorder窗口内899条LocalizationStatus全部有效，MapStatus一直ready。
- 三张快照共享epoch/map_id/frame，source age 0.102–0.152秒；错误epoch／map_id拒绝检查通过。快照每次遇少量`no_fresh_fused_depth`后等待fresh map再成功。
- live EGO probe的freshness为0.112／0.017秒，身份保持稳定；VINS body sphere仍有1,809 unknown／397 free／0 occupied，goal以`full_curve_planning_failed`拒绝，0条曲线、0条迟到曲线。No-control graph中无PX4或控制publisher。
- 新增 [机器报告](../evidence/n06-continuous-yaw-observation-20261023-101.json)、[证据报告](../evidence/n06-continuous-yaw-observation-20261023-101.md) 与 `n06_yaw_continuous_15deg_quarter_accel.json`。
- CURRENT、GOAL、execution plan、milestones及N06主报告更新为r27唯一子项；父目标保持`in_progress`，原出口未改。

## 验证

- r26 runner exit 0；三张快照、planner-only live probe和45秒输入记录完成；容器及匹配进程已停止。
- r27 profile复算：一次加速、59个匀速phase、一次减速，共15°nominal；角加速度、peak rate与r26一致；起始hold5秒、末端hold约5.164秒。
- 状态写回后运行`python3 tools/project_status.py`、profile/static consistency check、`git diff --check`和`git status --short --branch`。结构检查不替代N06正向验收。

## 限制与下一步

r26仍未得到body sphere free，live EGO无曲线，故不支持N06正向入口。下一步以相同连续低速运动扩展至15°，观察定位能否保持且未知体积是否下降；unknown policy与N05预算不变。
