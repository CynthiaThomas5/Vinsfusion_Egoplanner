# N06.4 r26 continuous 2° yaw pilot

日期：2026-10-23。Goal 完成模式，范围 N06。父目标 N06/S4 保持 `in_progress`。

## r26 结果

r26 用一次加速、匀速巡航、一次减速执行2°连续转向，保留r25角加速度`0.0026179939 rad/s²`、峰值速率约`0.00337982 rad/s`、wall位置和surround。debug truth累计yaw为2.0116°。Input recorder期间899条LocalizationStatus全部有效；MapStatus始终`input_ready=true`，epoch=`0cb03673a84f4841aace46c55352dd84`，map_id=`…-491022296e814dc393737bccaae70d22`。

三张snapshot均保持相同epoch/map/frame，source age分别为0.152、0.102、0.138秒（上限0.4秒）；snapshot服务前后MapStatus均ready且identity不变，错误epoch和map_id拒绝检查均通过。每张snapshot都遇到少量`no_fresh_fused_depth`瞬时拒绝，服务等待fresh数据后成功保存。VINS日志虽有短暂零特征帧，但没有健康锁存。

实际VINS body sphere query仍为`unknown`：1,809 unknown、397 free、0 occupied cells。Freshness为source 0.112 s、fusion 0.017 s；无控制planner probe发布一个compute-only goal，返回`full_curve_planning_failed`，0条曲线、0条故障后的迟到曲线。图中没有PX4／controller／setpoint或控制topic。因此 r26 证明连续2° pilot 可保持定位和fresh map，却没有形成正向N06入口，N06仍未通过。完整哈希、快照和probe数据见[机器报告](n06-continuous-yaw-observation-20261023-101.json)与[运行目录](../../artifacts/runs/n06-20261023-wall-r26/)。

## 下一项：r27 连续15°观察扫描

唯一主要变量为连续扫描名义转角从2°扩展至15°；角加速度、峰值速率、运动形式、位置和wall surround不变。目的是增加unknown body／hold邻域的视场覆盖，同时保留r26证明可行的连续转向方式。

profile：[n06_yaw_continuous_15deg_quarter_accel.json](../../config/components/simulation/n06_yaw_continuous_15deg_quarter_accel.json)。

```bash
bash tools/run_n04_map_layout.sh n06-20261023-wall-r27 wall_box_column 90 motion_n06 config/components/simulation/n06_yaw_continuous_15deg_quarter_accel.json
```

pilot成功标准为LocalizationStatus有效至至少15°实际truth yaw、同一MapStatus identity持续ready且depth新鲜，并取得三张匹配snapshot。之后复查真实VINS body／hold sphere和live EGO结果；unknown仍拒绝，不能把此pilot或合成组件检查当作N06通过。
