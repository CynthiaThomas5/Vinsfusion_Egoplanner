# N07 #197 对话摘要：hover freshness safety abort

## 用户约束

- 继续 Goal 完成模式，限定 N07，原门限和三次连续成功出口不变。
- N05 完整准入前不飞行；N07 失败后保留未通过状态，不把短飞记作通过。
- 地下空间不是飞行区域，不以地下 unknown 排除作为飞行许可。

## 本轮结果

固定条件下 N05 支架扫描 12/12、summary 14/14、post-release/current-area online/offline gate 通过。helper 的 cleanup status error 和 remove ack=false 保留；attachment 状态、Gazebo model list 及独立安全读回均确认 fixture detached/absent、PX4 disarmed/landed、bridge disabled。

无目标 runner 到达 ACTIVE 后，悬停仅 2.16 仿真秒，未发送导航目标，随后主动 disable 并 landed/disarmed；evaluator 仅 30 秒时长项失败。时序上 hold end 时 localization status 年龄约 0.353s，超过不变的 0.2s freshness 条件；下一 valid status 在记录的 hold end 之后到达。其他多条流同一时刻有约 0.34–0.38s 接收间隔。最可能是 runner 的 freshness fail-closed 引发提前退出，但底层共因尚未确定。`px4_preflight_failed` 是最终 bridge readiness 字段，不能单独解释中止。

ULog 12/12 和 graph 三快照均通过；N07 独立 evaluator 10/11。项目安全停止 exit 0、容器 Exited(0)。报告：[N07 #197 失败证据](../../progress/evidence/n07-no-goal-hover-failure-20261024-197.md)。

## 下一步

streak 仍为 0/3。#198 用相同固定 recipe 做新的 independent cold start，维持 freshness 门限并观察接收间隔是否重现；地下空间不作为飞行体积。
