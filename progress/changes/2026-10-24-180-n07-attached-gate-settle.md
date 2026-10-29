# N07.26 #180：attached N05 freshness 时序复核

## 执行模式与范围

Goal 完成模式；用户指定 N07。#179 使连续合格计数重置为0/3。仅诊断并继续 N07；保持固定镜像、runtime、支架profile、N05规则／阈值、悬停前置与验收出口。

## 证据、假设与唯一变量

#179 完成12/12支架阶段，attached N05 gate因“map source, fusion, or snapshot age exceeds the N05 freshness limit” fail-closed，没有解锁。fixture释放后，同 epoch/map 的 post-release gate新鲜接受，snapshot/source/fusion age为0.108/0.156/0.028秒。此结果支持但不能证明：刚完成支架回位后的地图更新短暂未赶上attached gate读取。

唯一主要变量：`n05-prescan-ready` marker产生后保持fixture附着、PX4 DISARMED，先等待2墙钟秒再运行相同的attached N05 live/offline gate。等待不改变阶段规则、数据年龄门限或结果；没有准入仍停止。其他镜像、runtime、profile、配置、目标和健康门保持不变。

## 完成标准与边界

- 使用全新container与epoch，初始N05拒绝时仍按规则先完成12/12支架扫描。
- ready marker后等待2墙钟秒，取得attached online/offline门；若拒绝/报错，不解锁，立即安全释放、独立确认fixture absent与landed/disarmed并记录失败。
- 若attached gate通过，按既有顺序完成release、post-release/current-area online/offline gates。同epoch/map，全部fresh接受后才能检查hover前置。
- 只有所有前置fresh且安全，才执行至少30仿真秒no-goal hover，并保留独立误差、PX4 EV/GNSS/ULog、ROS graph和最终landing证据。
- 单轮成功成为新序列1/3；任一出口失败仍为0/3。不得降低门限。

## 当前结果

#180 通过，成为 #179 失败后重置序列的第 1/3 次。ready marker 后保持 fixture attached、PX4 DISARMED 等待 2.000070387 秒；attached N05 online/offline gate 接受且 freshness 为 snapshot/source/fusion 0.112/0.132/0.032 秒。post-release 与 current-area gate 也 fresh 接受；三者均为 epoch `8a9263cc95ee41b5ab124cef107fc9d5`、map_id `8a9263cc95ee41b5ab124cef107fc9d5-a5b809525f3a417aa6fa23c0f50d1f6b`，N05 汇总 14/14 检查通过。

支架路线完成 12/12，attached→detached，fixture 已移除且 `fixture_may_remain_attached=false`，最终 landed。helper 的 `fresh DISARMED status is required for every fixture command` 错误和 exit 1 原样保留；其余阶段、N05 gate 和独立飞行证据另行评估，没有把 helper 错误改写为成功。

无目标悬停 30.0 仿真秒（33.488 墙钟秒），未发送导航目标；flight PASS，定位状态 670/670 有效，独立 evaluator 11/11 PASS。PX4 ULog 12/12 检查通过，53 个空中 estimator samples 中 EV position/yaw/velocity/height 全部有效、GNSS aiding 为零；ROS graph 三个只读快照含空中快照，唯一 bridge 控制发布者检查通过。末态 LANDED、disarmed。完整报告见[证据](../evidence/n07-no-goal-hover-20261024-180.md)及[结构化哈希记录](../evidence/n07-no-goal-hover-20261024-180.json)，原始文件在 `artifacts/runs/n07-20261024-180-01/`。

两秒等待与 attached gate fresh 接受相符，支持 #179 的短暂 freshness 时序假设，但不能单独证明因果。下一子项 #181 在同一固定版本保留两秒等待并启动新的独立 cold start；门限和验收条件不变。
