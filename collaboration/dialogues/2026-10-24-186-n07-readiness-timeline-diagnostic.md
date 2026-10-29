# N07 #186 对话摘要：定位状态转换时间线

## 约束

- 继续已授权的N07 Goal；必须完成3次连续cold-start验收。
- 不放宽定位门限和N05标准；失效时不得起飞。地下不是可飞空间。

## 结果与决定

#186在返回leg6启动只读VINS/status probe，捕获source 261.692s一帧normalized_cost=1.082783，status在261.796s转state4 invalid；后续raw cost回落但status仍invalid。关键主题没有>0.25s的观察间隔；根因已缩小为单帧残差异常，但异常的场景／运动成因未定。helper在6/12失败，自动detach并确认移除；PX4 disarmed/landed、容器exit0，无ready marker或飞行。计数仍0/3。

下一子项#187采用已由#165/#167/#168/#170验证过的`n06_full_airframe_retreat_240_oblique_early_view`支持路线，并从#187起保持该路线一致。详细报告见[证据](../../progress/evidence/n07-preflight-localization-failure-20261024-186.md)及[变更记录](../../progress/changes/2026-10-24-186-n07-readiness-timeline-diagnostic.md)。
