# N07 #193 对话摘要：同配方第二次独立冷启动

## 约束

- 继续用户授权的N07 Goal完成模式，目标为3次连续独立cold start。
- #192当时通过，#193失败后连续数归零为0/3。
- #193使用全新SITL，固定同一image/runtime/spawn/layout/support profile、N05/health/control thresholds、30秒no-goal hover、read-only observer set及ACTIVE后graph捕获。
- optional VIO freshness probe未运行；控制/验收门槛或源配置没有改变。
- 保留raw bridge timeline；对同阶段重复行做透明、可复算phase-transition projection，运行原始N07 evaluator。

## 结果

#193的N05 14/14、30秒no-goal hover、ULog 12/12、定位/遥测稳定和最终landed/disarmed均通过。Graph触发器已经看到ACTIVE+armed，但capture recorder首快照的bridge_status为空、四个PX4 control topic均0 publisher；后两快照均为唯一bridge publisher且无truth。strict reconcile失败，独立evaluator 10/11，唯一失败是graph owner，故不计cold-start通过，连续数归零为0/3。fixture helper错误保留；容器Exited(0)。

下一步#194保持飞行条件和observer负载不变，只在run-local graph capture recorder内部等待其自身DDS discovery看到ACTIVE+armed和四个唯一bridge publisher后采首快照，最多等待5秒；超时保留失败数据。
