# N07 #199：悬停前定位状态停滞

## 结果

**FAIL_PRECONDITION；连续成功数从 1/3 归零为 0/3。** 独立冷启动运行目录：[n07-20261024-199-01](../../artifacts/runs/n07-20261024-199-01/)。N07 保持 `in_progress`，下一项为 #200。

本次没有起飞。no-goal runner 等待 60 秒后仍未满足 bridge/map 前置，状态为 `DISABLED`，原因 `localization_not_tracking`；flight 结果是 `FAIL / vio_bridge_map_preconditions_not_ready`。没有 goal、位置命令、PX4 轨迹设定点或控制服务调用，悬停时间为 0。

## 固定条件与 N05 证据

运行使用固定镜像 `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`、runtime 配置 SHA-256 `1ddd6838ae2a678f89547ce90eea849582edcc29cddab341667bd2d1d9d3e360`、runtime-contract 文件 SHA-256 `856bf1f2222a5286493813c9702731f7e5166844eb2bfd98c6f525f3f36924eb`、spawn `-6.5,0,0.3,0,0,0`、`wall_box_column` 布局与 `n06_full_airframe_retreat_240_oblique_separated_return` 支架路线。健康、准入、控制、flight 与 evaluator 门限均未变，也未启动可选 freshness probe。

- 初始 online/offline N05 gate 一致拒绝 `ground_plane_insufficient_raw_occupied_voxels`。支架路线完成 **12/12** 阶段，attachment 为 `attached → detached`，remove service ack 与 Gazebo 场景缺失确认均为 true。fixture trace 共 **13,247** 行、单 epoch、0 条 invalid localization row。
- fixture helper 的最终 `outcome=failed`，错误为 `localization changed or became invalid during physical scan`；该状态如实保留。结合 12/12 阶段、已脱离移除、cleanup 未启动及 trace 全部 valid，报错很可能发生在脱离后的最终健康轮询；精确触发条件没有被工具保存。N05 汇总的 **14/14** 独立检查仍全部通过。
- 扫描后、post-release 及单独重采样的 current-area online/offline gate 均接受 `all_entry_phases_known_and_clear`，epoch `3670f97437f548c289dffd105c6fb746`、map `3670f97437f548c289dffd105c6fb746-03d8576ce3a04a01ab149224ecb5466a` 保持一致。current-area freshness 中 snapshot age 为 0.108s、融合源龄 0.032s。
- 起飞前独立释放安全读回 **9/9** 通过：bridge DISABLED、无控制、PX4 disarmed/landed、夹具不存在、N05 summary 通过，且没有活动飞行或观察器进程。

N05 的地面平面是起降／接地边界检查的一部分。本次 runner 在上锁状态下因定位前置拒绝，没有地下飞行或地下目标；地下空间没有作为可飞区域。

## 准入失败证据

定位状态从 runner 收到的首个样本起就为 `state=4, valid=false, reason=clock_stalled`。首个样本 wall elapsed 1.791s，状态时戳 590.340s、源时戳 576.748s，相差 13.592 仿真秒；约 61.73s 等待结束时，状态时戳为 644.216s，源时戳仍是 576.748s，差值 67.468 仿真秒。1,200 个定位状态样本的源时戳保持不变，`accepted_optimized` 固定为 8,602。

只读对齐观察器记录到 PX4 local position、VINS raw odometry 继续更新（raw odometry 最后源时戳 644.296s），但观察窗口没有 `/localization/optimized_imu_odom` 样本。同期 VINS telemetry 的 solver 仍 usable，末尾 normalized cost 约 0.432；仿真时钟无回退。证据指向定位适配输出没有继续接收／发布优化里程计，**其根因尚未确定**。

Graph waiter 因 flight 结果在 bridge 进入 ACTIVE+armed 前已写出而退出；本次没有 graph snapshot，不能计为唯一 bridge publisher/no-truth 出口通过。N07 hover evaluator 与 EV airborne ULog 验收也未执行，因为没有 ACTIVE/armed flight。

## 安全收尾与下一步

起飞前与失败后的独立安全读回分别 **9/9** 通过。失败后 bridge 仍为 DISABLED，PX4 未解锁且 landed；`bash tools/project.sh stop n07-20261024-199-01` exit 0，容器状态 `exited 0`，活动项目容器数为 0，观察器及 flight runner 均已结束。

本次失败使连续计数归零。#200 采用新的 cold start，保持镜像、runtime、spawn、layout、支架路线、observer 集合、30 秒要求及全部原门限不变；若定位状态再停滞，按同样证据追踪来源时间、优化里程计与适配状态，不放宽门限。

逐项文件 SHA-256 及机器可读判定见[JSON 报告](n07-preflight-localization-stall-20261024-199.json)。
