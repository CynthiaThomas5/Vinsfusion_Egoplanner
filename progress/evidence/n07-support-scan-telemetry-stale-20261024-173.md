# N07 #173：路线健康改善，但 N05 gate 遇到 telemetry stale

## 结论

#173用缩短斜视的既有`oblique_separated_return` profile完成12/12全机支架扫描，VINS `accel_bias_norm`最高0.083839，没有重现#171/#172的bias越线。随后attached和post-release N05 live gates均缺少adapted odometry并超时；定位adapter锁存`telemetry_stale`、bridge DISABLED。没有正向release gate，也没有flight或hover结果；N07连续悬停计数仍为0/3。

## 固定条件与初始拒绝

- Run：`n07-20261024-173-01`；epoch `483200e387ae430d99626cf9c8e27a37`。
- 固定镜像：`sha256:099ab9afecd28b7354f6d6494944b1db30c7c67c973e9b93b03f87aca7ad6f8`；runtime contract SHA-256：`856bf1f2222a5286493813c9702731f7e5166844eb2bfd98c6f525f3f36924eb`。
- `wall_box_column`、spawn `-6.5,0,0.3,0,0,0`；相较#172只切换到既有`n06_full_airframe_retreat_240_oblique_separated_return` profile。
- 初始N05 online与offline一致拒绝`TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`；未绕过raw unknown。

## 路线与N05结果

支架runner完成12/12并返回起点；ready marker为attached、`truth_input_used=false`、`control_or_goal_published=false`。扫描bias峰值0.083839 m/s²，低于既有0.15界；solver维持usable。这支持较短pitch暴露可避免本轮bias越线的假设，但不能证明其为#171/#172的根因。

attached gate和released gate各按120秒原等待超时，错误均为`missing=['odom']; received=['bridge','clock','localization','map']`。两者均未产生准入结果。失败时localization status为`telemetry_stale`：attached检查期间header/clock约487.572秒、source stamp 386.136秒；bridge `DISABLED/localization_not_tracking`。

post-release只读回读时，raw VINS estimator telemetry已发布stamp 555.292秒、raw VINS odometry stamp 556.744秒，而localization adapter仍保留source stamp 386.136秒、state 4/`telemetry_stale`，且optimized odometry缺失。raw输出后来恢复不能解除adapter同epoch锁存，也不能代替N05 release gate。现有证据未捕获第一个源间隔，故还不能判定故障起于raw发布、DDS接收还是adapter处理。

## 安全收尾

fixture runner报告已detach、Gazebo场景fixture模型不存在、final landed且vehicle state DISARMED。`failure-safety-readback.log`确认bridge DISABLED/unarmed/landed、PX4 arming state 1、land detector landed。项目stop流程成功，容器exit0且无活动项目容器。没有发布导航goal、解锁或飞行。

## 产物与下一步

原始数据位于[`artifacts/runs/n07-20261024-173-01/`](../../artifacts/runs/n07-20261024-173-01/)，包含N05初始／attached／post-release结果、12阶段支架与VINS bias时序、health readback及post-timeout raw source readback。SHA-256见[JSON证据](n07-support-scan-telemetry-stale-20261024-173.json)。

#174沿用短斜视路线和所有门限，用已有只读freshness probe贯穿扫描与attached gate，记录raw telemetry、raw odometry、adapted odometry、status及clock，判定首个断档位置。只有attached与released gate fresh通过才可进入N07 hover；不放宽门限、不绕过准入。
