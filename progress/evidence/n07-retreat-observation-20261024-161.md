# #161 N07 远端俯视观察结果

run `n07-20261024-161-01` 使用spawn `(-6.5,0,0.3)`和1.8m后退路线。初始N05在线与离线结果一致，因raw-ground plane候选体素为0而拒绝；当时bridge DISABLED、未解锁且PX4报告landed=true。

## 扫描与定位结果

9阶段profile完成阶段0–5：后退、远端pitch转入+0.45rad、保持15s并复位。实际pitch最大+0.46299rad；这些阶段定位和epoch连续。x返程阶段6于sim 162.02s开始；mapping adapter在sim 184.108s记录`normalized_cost_exceeded`并清图。返程只到x≈−1.592m（目标x=0），随后fixture安全清理回到起始支撑点，profile不完整。

- 返程到门关闭时的157条VINS telemetry记录：long tracks最低97、stereo features最低147、加速度bias最高0.07137m/s²。全run bias峰值0.13677m/s²，未越过0.15门限。
- 门锁存状态cost=1.08510。fixture trace末尾仍重复旧的有效status/cost=0.42753；不能把该延迟状态当作定位恢复。门关闭后的VINS记录derived normalized cost最高1.211，且当时long tracks仍为126，显示本次cost越线不是由极少跟踪数伴随。
- 没有`n05-prescan-ready.json`，也没有attached/released post-scan N05结果；本run无法判断俯视是否减少了近地unknown。

## 安全结果

fixture helper执行return-to-home清理并确认detach；remove服务已确认，Gazebo model list中无fixture，`fixture_may_remain_attached=false`。全部记录PX4 arming state为DISARMED，项目容器Exited(0)。本run没有记录恢复后最终PX4 LandDetected样本；初始检查报告landed=true，清理记录确认支架脱离和模型移除。无解锁／飞行，N07 hover仍0/3。

## 下一步

#159–#161都在加入远端姿态观察后于x返程时触发cost锁存；#160/#161的跟踪数和bias均未越线，单靠yaw复位时机或pitch复位时机尚不能解释。下一项#162保持+0.45rad俯视贯穿x返程，只把pitch复位从远端移到home；假设持续观察地面边界附近的视觉纹理能减少返程中的cost尖峰。仍按同一fresh released N05五阶段在线／离线门限验收，未通过不解锁。

机器可读摘要：[n07-retreat-observation-20261024-161.json](n07-retreat-observation-20261024-161.json)。初始独立复算：[n07-n05-before-offline-replay-20261024-161.json](n07-n05-before-offline-replay-20261024-161.json)。静态路线：[geometry JSON](n07-retreat-180-pitch045-route-geometry-20261024-161.json)。原始日志与哈希位于`artifacts/runs/n07-20261024-161-01/`。
