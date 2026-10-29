# N07.31 #185：返回段代价尖峰后的新冷启动

## 执行模式与范围

Goal 完成模式；用户指定范围N07，父目标`in_progress`，当前连续合格cold start为0/3。只运行新container/epoch，固定版本与验收条件不变；不修改源码、配置、健康门、N05门限或地下边界。

## 已有基础与判别信息

#182在固定支架路线完成12/12并取得三阶段fresh N05 gates和30秒no-goal hover，曾成为1/3。#183、#184均在支架扫描返回段第7/12阶段失去定位，连续计数按规则复位。#184记录到一条VINS遥测代价尖峰（final_cost=8620.226283557802、4444 residual components、normalized cost=1.969642），与health status拒绝数值一致；后续低代价有效解不覆盖失效。该证据支持原门限正确fail-closed；本子项不尝试放宽门限。

## 固定条件与完成标准

- 新container/epoch；镜像`sha256:099ab9afecd28b7354f6d6494944b1db30c7c67c973e9b93b03f87aca7ad6f8`、embedded contract SHA `12b1c17cccfcb5c9f035516baa3d40c05ab7b8a4d5c32c4e28bef47d15b46233`、spawn `(-6.5,0,0.3,0,0,0)`、wall layout与profile `n06_full_airframe_retreat_240_oblique_separated_return`保持不变。
- 初始拒绝保持只读记录；ready marker必须匹配本run、attached、DISARMED、无truth/control。marker后明确等待2秒，只运行一次attached online/offline gate。
- attached、post-release、current-area gates需同epoch/map且满足原0.4秒freshness。任一拒绝时不发送控制，detach、独立readback、停止容器。
- 全部前置通过后执行30仿真秒no-goal hover，按既有独立误差、EV/GNSS/ULog、graph唯一控制publisher及最终落地上锁出口核验。成功后为新的1/3。

## 当前状态

待执行。固定run目录：`artifacts/runs/n07-20261024-185-01/`。
