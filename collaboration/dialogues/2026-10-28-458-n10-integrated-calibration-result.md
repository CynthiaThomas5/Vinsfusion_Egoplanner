# N10.3/#458 综合正常导航校准结果

- 用户授权继续完成 N10，并明确按 #434 跳过故障注入与故障后校准。
- #458 用 `max_cnt=220` 完成一次正常 16 m 任务、动态箱体重规划、20 sim s 保持和正常降落；PX4/bridge landed、disarmed、control-disabled、zero-control，未使用紧急 disarm。
- 独立整体结果为 `INSUFFICIENT`。normal action、arrival、raw VIO draft numeric gates、地图来源/更新 age、快照与 voxel trace、sensor capture、contact 通过；连续净空因 kinematics observer 0 records 不足，tracking threshold、resource/queue basis、replan metric basis 仍未建立。
- 已定位 observer 零记录的具体源头：PX4 启动时按 `PX4_GZ_MODELS` 直接 file URI 选根模型，旧路径没有指向 run-local instrumented wrapper。
- 原始 #458 归档不修改；校准不计 N15/N16 正式次数。下一个子项 #459 仅做未解锁、无目标的启动诊断。
