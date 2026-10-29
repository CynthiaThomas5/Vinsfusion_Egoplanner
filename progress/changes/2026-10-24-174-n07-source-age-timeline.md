# N07.20 #174：定位输入与adapter输出时序诊断

## 执行模式与范围

Goal 完成模式；用户指定范围N07，父目标`in_progress`。#173的`oblique_separated_return`路线完成12/12且VINS accel bias峰值0.083839，但attached与released N05 gate均缺少adapted odom并锁存`telemetry_stale`，因此没有hover资格。当前连续成功数为0/3。

## 证据与假设

#173 failure-time localization status保留source stamp 386.136，gate时clock为487.572；之后只读查询显示raw VINS telemetry stamp 555.292和raw odometry 556.744，而adapter仍锁存旧stamp，optimized odom缺失。观测到raw输出在锁存后恢复，但没有完整的跨失败订阅时间线，尚不能判断首次故障是VINS输入topic gap、adapter订阅／执行延迟，还是数据到达次序问题。

假设：#173当前门禁失败由一次冷启动内的raw输入／adapted输出时序断档触发health latch。主要运行变量是独立cold-start epoch；附加一项只读观测，用已有`probe_vio_stream_freshness.py`贯穿整个支持扫描与attached gate，记录`/clock`、raw VINS telemetry/odometry、adapted optimized/propagated odom及status。该探针不改变控制、参数或健康判断，并不覆盖任何门禁。

## 完成判据与下一步

沿用#173的fixed image、runtime、wall world、spawn、`oblique_separated_return` profile、N05 gates和health limits。attached/released gates均须fresh通过才可进入同epoch no-goal hover；任何缺少odom、health lock或map拒绝都停止飞行并完整保存时序。若raw topics连续而adapter output停止，证据支持定位适配器链路问题；若raw源也出现超龄／断档，则把上游VINS／调度作为待定位项。不得放宽0.15 bias、freshness或N05条件。

若门禁通过，完成N07原定至少30仿真秒hover及所有独立EV、PX4、无GNSS／无truth和落地检查。若门禁失败，按采样时间线定位首个断档，再决定最小修复；不盲目重复原route。

## 结果

#174失败于支架扫描stage4（目标pitch 0.45 rad），完成4/12；sim 220.508s的status锁存`normalized_cost_exceeded=1.162528`。对应VINS telemetry位于220.408s，final_cost=2958.369、residual_components=4378，accel bias=0.00822m/s²、long tracks=102、stereo features=131、solver仍usable。相邻telemetry q为0.35570和0.33042，说明越线来自一个孤立高代价样本；门按原规则锁存，未绕过。

只读probe覆盖378.4墙钟秒。raw telemetry/raw odometry最大source gap均0.096s，双目最大0.068s；raw VINS与传感器在定位锁存后继续到sim约304.3s。adapter propagated/optimized odometry在锁存后停止，status继续发布当前clock与锁存状态。因此#174没有复现“raw source断档先于adapter停发”，也不能据此回溯解释#173的`telemetry_stale`。同profile #138、#148和#173此前pitch阶段q峰值约0.773、0.823、0.665；本次孤立尖峰原因未定。求解耗时无明显增加，不能归因于probe负载。

初始N05在线／离线仍一致拒绝raw unknown；扫描未产生ready marker，未运行attached/released gate、flight或hover。runner已detach并确认移除fixture，PX4 landed/disarmed，容器`Exited(0)`。健康门／N05规则未改，连续悬停计数仍0/3。数据与哈希见[证据报告](../evidence/n07-support-scan-normalized-cost-failure-20261024-174.md)。

下一项#175使用同一profile、版本、spawn及门限，唯一主要变量为不启动额外高频只读VIO流探针；保留runner原生VINS/odometry/status记录。目的是检验附加observer是否影响孤立代价尖峰，同时争取完成N05 gates；只有attached和released gate fresh通过才进入同epoch no-goal hover。若相同位置再次越线，停止重复该路线并按新的证据缩小pitch转入动作。
