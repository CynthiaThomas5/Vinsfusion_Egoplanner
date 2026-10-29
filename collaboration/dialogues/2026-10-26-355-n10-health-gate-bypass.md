# #355 N10 定位健康门诊断旁路

用户要求关闭健康门限制并继续。按已沟通范围，为下一次 N10 诊断 SITL 增加运行时定位健康策略旁路；不改正式验收阈值，不把旁路运行计为定位健康资格。保留真实 VINS cost、特征、残差、时序与旁路原因；malformed input、时间戳/epoch/身份完整性、碰撞/map 规则和 PX4/bridge 状态保护继续生效。

沿用 #354 的 0.8 m/s/轴、5 m horizon、16 m 单程目标、spawn、3 s 到达驻留和 600 s ACTIVE hold，只改变诊断旁路开关。测试通过后已冻结 #355 runtime contract 和 run protocol；SITL 尚待运行/归档。

## Run result

#355 reached the 16 m goal, passed independent arrival/dwell and held ACTIVE for 600 simulated seconds. The run-scoped quality/freshness policy bypass was observed, with normalized cost peaking at 1.766 while the 1.0 configuration stayed unchanged. The run is not a complete pass: four observers ended at their 380-second cap, so contact landing and complete raw-VIO/alignment evidence are missing. Independent terminal readback was safe and the container was stopped. #356 changes observer lifecycle only and repeats the same route/profile. See the [#355 result](../../progress/evidence/n10-upstream-spline-speed080-health-bypass-16m-20261026-355.md).
