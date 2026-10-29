# N07.43 #197：no-goal hover freshness safety abort

## 模式与执行范围

Goal 完成模式，用户指定 N07。#196 的 VINS health failure 已将 streak 清零；#197 按同一固定镜像/runtime/spawn/layout/support profile 开始新 cold start。N05 全流程准入通过后执行 no-goal hover、独立 ULog/evaluator/graph 验证与安全收尾。未改项目源码、配置、flight runner、健康门限或验收标准。

## 结果

N05 支架路径 12/12，summary 14/14；post-release 与当前 area online/offline gate 一致接受。helper 自身报 `fresh DISARMED status is required for every fixture command`，remove-service ack 缺失；保留原错误。attachment 记录 attached→detached，fixture 标为 removed 且 `fixture_may_remain_attached=false`；Gazebo model list 及独立 disarmed/landed/bridge-disabled 读回确认现场无 fixture。

flight runner 到达 ACTIVE 并起飞，但 hold 只完成 2.16 仿真秒后安全请求 disable，无 goal，正常 landed/disarmed。evaluator 10/11，唯一失败是 30 秒 hold 时长。时间戳显示 hover end 时最后定位 status 已陈旧约 0.353 秒，超过 runner 固定的 0.2 秒限制；下一条 valid status 在 hold end 后约 0.0006 秒到达，多条流在同一墙钟窗口也出现约 0.34–0.38 秒接收间隔。将其作为最有证据支持的 loop-break 推断；共因根源未确定，详见[中止时序分析](../../artifacts/runs/n07-20261024-197-01/n07-hover-abort-analysis.json)。终态 `px4_preflight_failed` 不是直接触发证据；该 bridge readiness reason 在 disabled 阶段已出现，且 #194/#195 均有此初态并通过。

ULog 12/12，graph 3/3 snapshots 均通过。后飞行安全读回通过，`project.sh stop` exit 0、容器 Exited(0)、活动项目容器 0。保存后的 safety JSON 重读验证通过；原 host 格式化命令在已写入文件后打印摘要时报错，该情况及验证结果一并记录。

完整报告：[N07 #197](../evidence/n07-no-goal-hover-failure-20261024-197.md)。

## 下一步

N07 streak 保持 0/3。#198 以同一固定 recipe 执行新独立 cold start；保持 0.2 秒 status freshness 门限，观察短接收间隔是否重现。N05 地面边界逻辑仍仅用于入口／接地准入，不表示或生成地下飞行区域。
