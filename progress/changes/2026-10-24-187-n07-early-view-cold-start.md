# N07.33 #187：early-view支架路线bias健康门失败

## 执行模式与范围

Goal完成模式；用户指定范围N07。#187按已有N07历史选择early-view做一次主变量替换；保持image/runtime、源码、spawn、wall布局、健康/N05门限和hover参数不变。冷启动未达飞行资格，连续通过计数仍0/3。

## 实际结果

新epoch `f58b25c520d545e09a4fb3575d148bb6`。初始N05 online/offline一致按raw unknown拒绝。支架扫描第7/12阶段helper exit1，错误原文`localization changed or became invalid during physical scan`，定位reason `accel_bias_norm_exceeded`、normalized_cost=0.531617。配置bias门限为0.15 m/s²；VINS遥测于source 250.276s首次达到0.150161，随后最大0.187644，支架轨迹约x−2.361m/z1.0m处于pitch回正后回程。没有ready marker或gate。

## 安全收尾与后续

helper verified detached、fixture移除、scene absent；557条PX4状态全DISARMED，303条LandDetected全landed。独立readback bridge DISABLED/localization_not_tracking、PX4 disarmed/landed。`bash tools/project.sh stop n07-20261024-187-01`后容器exit0、无活动项目容器。报告见[Markdown](../evidence/n07-preflight-health-failure-20261024-187.md)和[JSON](../evidence/n07-preflight-health-failure-20261024-187.json)。

early-view没有通过；#188回到#180/#182已用且通过过的separated-return support profile，继续新cold start，所有门限保持不变。若成功，从#188起冻结该profile连续完成序列。
