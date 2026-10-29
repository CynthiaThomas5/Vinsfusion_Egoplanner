# N07 #175：分离返回路线无额外probe复核

## 用户约束

- 用户已授权Goal完成模式，范围N07，持续至出口通过。
- 不降低health、N05或N07门限；无fresh attached与released准入不得飞行。
- N06 ground-boundary工作已完成，不在N07中重开。

## 证据与决定

#174在stage4 pitch转入出现单个normalized-cost=1.162528样本并锁存健康失败；probe确认raw VINS与相机源持续新鲜。#173在相同profile的pitch段未见越线，求解耗时也与#174接近，因此observer是否相关未知。#175保持profile、版本和其余条件不变，只移除额外高频只读probe，保留runner原生诊断。如果support scan、attached/released N05 gates均通过，则在同epoch继续no-goal hover；否则安全停止并按新证据定下一项。

## 本项结果

#175完成12/12支架；VINS cost峰值0.835579、bias峰值0.095803m/s²，attached N05 online/offline fresh gate一致接受。fixture移除和安全回读确认后，post-release gate因missing optimized odom超时，localization锁存telemetry_stale；没有解锁、flight或hover，容器Exited(0)，N07仍0/3。详情见progress/evidence/n07-support-scan-attached-pass-release-stale-20261024-175.md。

下一项#176只在attached gate通过后启动read-only VIO时序probe，观察fixture release与post-release N05 gate期间的raw/adapted输入输出；支架扫描不加probe。gate正向通过前不飞。
