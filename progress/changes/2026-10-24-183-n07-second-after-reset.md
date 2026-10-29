# N07.29 #183：重置后的第二次连续悬停冷启动

## 执行模式与范围

Goal 完成模式；用户指定范围N07。父目标保持`in_progress`。#182通过后为1/3；#183未达到飞行前置条件，故连续计数重置为0/3。

## 实际执行与结果

使用固定镜像、runtime contract、spawn、wall layout和`n06_full_airframe_retreat_240_oblique_separated_return`，新epoch为`d19007b088ff45ed9a6418dd04718064`。初始N05拒绝原因为`TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`。支架扫描在第7/12阶段因VINS定位失效停止：`normalized_cost_exceeded`，normalized_cost=`1.0589551679721994`；helper错误原文为`localization changed or became invalid during physical scan`。ready marker没有生成，因此attached gate和飞行均未启动。

## 安全收尾与验证

helper报告cleanup attempted、detached verified，fixture移除及场景模型缺失确认均为true；588条PX4状态均DISARMED、312条LandDetected均landed。独立读回：bridge DISABLED/`localization_not_tracking`、armed=false、landed=true；PX4 arming_state=1；Gazebo列表无fixture。`bash tools/project.sh stop n07-20261024-183-01`后容器`exited 0`且没有活动项目容器。

## 产物、局限与下一步

失败报告：[Markdown](../evidence/n07-preflight-localization-failure-20261024-183.md)及[JSON](../evidence/n07-preflight-localization-failure-20261024-183.json)。原始证据在`artifacts/runs/n07-20261024-183-01/`。无悬停／EKF2 N07飞行证据；健康门和门限均未改。下一子项#184用新冷启动和相同固定条件重试，失败继续fail-closed。
