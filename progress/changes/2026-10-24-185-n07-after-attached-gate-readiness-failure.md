# N07.31 #185：attached gate通过后readiness转为拒绝

## 执行模式与范围

Goal完成模式；用户指定范围N07。固定镜像/runtime、spawn、布局、支架路线和门限不变。此前N07连续计数为0/3；#185未生成飞行证据，不能增加计数。

## 实际执行与结果

新epoch `bdcee586935e43caba090bdd70d90fde`。初始N05入口online/offline一致按raw unknown拒绝。支架12/12完成，ready marker确认attached、DISARMED、无truth/control。marker后唯一一次2.000073489秒settle及attached N05 online/offline gate通过，同epoch/map，snapshot/depth/fusion freshness在原0.4秒内。

释放后helper exit 1并原样报告`localization changed or became invalid during physical scan`；fixture attached→detached，移除ack和scene absence确认。fixture最后定位单样本却为valid/state1。独立bridge readiness echo（第一次因ROS discovery race失败，第二次显式类型重试成功）显示`DISABLED/localization_not_tracking`，PX4 DISARMED且落地。两者时序不一致，因此未运行post-release/current-area gate或飞行，保守停机。

## 产物与下一步

报告见[Markdown](../evidence/n07-preflight-health-failure-20261024-185.md)及[JSON](../evidence/n07-preflight-health-failure-20261024-185.json)，原始记录在`artifacts/runs/n07-20261024-185-01/`及`artifacts/runs/n07-20261024-185-01-stack/`。下一子项#186用只读probe记录回程段raw VINS telemetry与LocalizationStatus转换，不改变验收阈值；只有post-release/current-area所有原有门fresh通过后才考虑no-goal hover。
