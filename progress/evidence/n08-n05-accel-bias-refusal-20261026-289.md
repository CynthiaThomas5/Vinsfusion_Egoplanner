# N08 #289：N05 支架扫描在回程被定位偏置健康门停止

## 结论

**N05 前置未通过；本次没有 N08 mission。** 新冷启动按既定 `n06_full_airframe_retreat_240_translation_only` 完成阶段0–2，在第3阶段（从 x=−2.4m 回到x=0）因 `/localization` 报告 `accel_bias_norm_exceeded` 停止。扫描器执行夹具detach/remove并确认 landed；PX4保持disarmed、bridge控制未启用。未获得释放后或mission current-area准入，没有goal、起飞、取消或制动数据。健康限值未改变。

## 触发样本

Run：`n08-cancel-translation-prescan-20261026-289`。配置的 `max_accel_bias_m_s2` 为0.15。`fixture-vins.jsonl` 的首条超限样本在source stamp 170.776s：bias=0.150019m/s²、stereo features=172、long tracks=129、solver usable=true、solve time=19.7ms、final cost=584.15。邻近轨迹在回程x≈−1.39m；normalized cost约0.503，说明本次锁存的具体原因是accelerometer-bias门，不是cost门、求解超时或地图身份变化。偏置随后最高0.154618m/s²。

| 同路线区段 | #288 bias最大值 | #289 bias最大值 |
| --- | ---: | ---: |
| outbound x≈−2.0m | 约0.009m/s² | 0.074m/s² |
| return x≈−1.4m | 约0.079m/s² | 0.155m/s²（超门） |

这支持“VINS估计在独立冷启动间发生了不同偏置漂移”的诊断；单次对照不能归因到初始化、视觉观测或其他内部机制。没有证据支持调整health阈值。

## 清理和安全读回

`fixture-result.json`记录fixture已从模型列表移除、`fixture_may_remain_attached=false`、最终landed。独立4s `probe_px4_bridge_live.py`读回bridge `DISABLED`、`control_enabled=false`、`armed=false`、`landed=true`；`vehicle_remained_disarmed=true`，control_mode、trajectory_setpoint和vehicle_command各0条。`bash tools/project.sh stop n08-cancel-translation-prescan-20261026-289`退出0，项目容器已停止。

## 下一步实验

#290保持扫描profile、模型、地图和限值不变，只换一次独立冷启动／VINS epoch，检验相同回程位置是否再次出现偏置漂移。标准不变：完成6/6、夹具移除和post-release online/offline N05均接受，才能进入N08 mission。若再次超限，保留拒绝并继续调查偏置来源，不绕过健康门。
