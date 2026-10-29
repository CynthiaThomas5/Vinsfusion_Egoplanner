# N07.32 #186：定位状态转换只读时间线

## 执行模式与范围

Goal完成模式；用户指定范围N07。固定镜像/runtime、spawn、wall布局与健康门限不变。#186唯一附加诊断变量是在回程leg 6启动现有只读`probe_vio_stream_freshness.py`，不发布truth或控制，也不替代任何准入门。

## 结果与判别信息

新epoch `3d56eed32e9e4f76896ff6a6789061a0`，初始N05入口按raw unknown拒绝。支架扫描在6/12阶段定位失败，helper原文`localization changed or became invalid during physical scan`。probe精确捕获source 261.692s raw VINS normalized cost `1.082783341561447`（final_cost=2558.806136595189、4365 residual components），LocalizationStatus于261.796s转换为state4 invalid、reason `normalized_cost_exceeded`；随后遥测cost回落，但invalid状态保持到probe end-marker尾窗。Clock、telemetry、status与odom最大观测间隔未显示>0.25s gap。单帧残差触发原因已证实，异常物理根因未明。没有改变门限。

## 安全收尾与产物

helper安全cleanup attempted/verified detached，fixture移除和scene absence确认；484条PX4 status全DISARMED、263条LandDetected全landed。独立readback bridge DISABLED/localization_not_tracking、PX4 disarmed/landed。无ready marker、N05 gate或飞行。容器`bash tools/project.sh stop n07-20261024-186-01`后退出0、无活动项目容器。报告：[Markdown](../evidence/n07-preflight-localization-failure-20261024-186.md)、[JSON](../evidence/n07-preflight-localization-failure-20261024-186.json)。

## 下一步

#187使用同镜像/runtime下曾在#165/#167/#168/#170全程支持扫描并完成30s hover PASS的`n06_full_airframe_retreat_240_oblique_early_view`路线；从#187开始固定路线作为新的连续序列，不改健康/准入阈值。
