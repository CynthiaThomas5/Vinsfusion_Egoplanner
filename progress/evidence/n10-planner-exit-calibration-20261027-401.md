# N10.3/#401：规划器进程退出故障闭环校准

## 结论

当前冻结运行身份下，规划器进程退出这一类故障的端到端校准通过，范围仅限本次单次校准。运行在活动目标期间对精确匹配的 ego_planner_node 进程发出一次 SIGTERM；navigation action 以 ABORTED 和原因 planner_ego_planner_process_exited_during_active_goal 结束。uav_px4_bridge 经正常安全降落路径到达 LANDED，PX4 landed 且 disarmed，控制关闭，终态后没有控制输出或旧目标/轨迹。没有使用紧急 disarm。该结果不是导航任务成功，也不计入冻结后的 N15 正式次数。

## 触发与响应

- 运行：n10-20261027-401-planner-process-exit-calibration
- runtime contract SHA256：1a9ceea19f771f149cb87045e5195c430345351d3128a162d8b83c5fc25292a9
- fault protocol SHA256：3acc7fc8a0391f39f7bf0399cf93f7e137e0c59eca35dfbf3155f59d5f80a020
- image：sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8
- goal/epoch：fe83b3e28e7643b1a0021ed3061de667 / a96cc8f3c6874a93a4dcb653f367d13f
- bridge 在信号前为 ACTIVE 且 armed；注入器确认 action status、goal、epoch 及 PID/start-time 身份后，在目标源时间后 5.0 仿真秒发出一次 SIGTERM。信号至观察到进程退出约 0.175 wall 秒。
- flight.json 中 action result 为 ABORTED，status 6，原因与 bridge fault reason 完全匹配。
- 15 秒独立末态读回均显示 bridge LANDED、landed、disarmed、control disabled；PX4 land_detected 为 true，终态后控制样本为零，旧 goal/trajectory 为零，终态违规为零。
- 接触评估通过：禁止接触 0，并观察到落地接触。

## 传感器记录

离线 sensor-capture evaluator 为 PASS：一个活动身份，4,315 条活动任务回执、25,369 条总回执和 25,314 条 MCAP 消息。55 条回执属于 MCAP 时间窗边界外的数据；内部没有回执/载荷缺口。该 PASS 只表示回执到无损包记录的完整性，不证明 VIO 质量、飞行验收或定位指标通过。

## 验证及限制

故障链的构建和回归依据见 [#392 故障路径审计](n10-fault-path-audit-and-observer-window-20261027-392.md)：17 个 ROS 包构建成功，471 项测试通过。本次 SITL 是当前版本的 planner-process-exit fault-to-terminal 量测。原始运行文件及关键哈希见本报告配套 JSON 和 artifacts/runs/n10-20261027-401-planner-process-exit-calibration/。

本次只校准规划器进程退出这一类别。深度/定位断流、epoch/进程重启、时钟回退等类别仍要逐项核对复用证据或补一次校准。N15 每类至少两次正式故障测试仍在 N10.7 冻结后进行。
