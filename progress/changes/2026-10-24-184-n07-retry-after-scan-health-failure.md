# N07.30 #184：支架定位健康失败后的全新冷启动

## 执行模式与范围

Goal 完成模式；用户指定范围N07。固定镜像/runtime、spawn、wall layout、支架profile和所有门限未变。#183失败后连续计数为0/3；#184再次未达到飞行前置条件，仍为0/3。

## 实际结果与诊断

初始N05 online/offline一致拒绝`TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`，bridge DISABLED、未武装、落地。支架扫描返回段第7/12阶段定位门拒绝，helper错误原文`localization changed or became invalid during physical scan`，last normalized cost `1.9696420427526087`。捕获的VINS telemetry在source stamp 328.252s有final_cost=8620.226283557802、4444 residual components，按既有公式复算normalized cost为1.969642；这是一条超过原1.0门限的代价尖峰，后续帧回落也没有覆盖health failure。该值与helper status吻合，为#183同一阶段的第二次冷启动拒绝提供了直接遥测证据。未改健康配置或门限。

## 安全收尾与验证

helper完成detach和移除，`fixture_may_remain_attached=false`；603条PX4 status全DISARMED，320条LandDetected全landed。独立读回为bridge DISABLED/`localization_not_tracking`、armed=false、landed=true；PX4 arming_state=1；场景无fixture。`bash tools/project.sh stop n07-20261024-184-01`后容器`exited 0`，无活动容器。没有ready marker、attached gate或飞行。

## 产物、局限与下一步

[失败报告](../evidence/n07-preflight-localization-failure-20261024-184.md)与[结构化报告](../evidence/n07-preflight-localization-failure-20261024-184.json)，原始证据在`artifacts/runs/n07-20261024-184-01/`。N07仍未完成。#185使用新cold start和相同条件继续取得连续成功；任一门失败就fail-closed，不反复用同epoch重试。
