# N07 #171：支持扫描中的 VINS 健康门失败

## 结论

#171未取得N07资格。新epoch启动期探针未见`telemetry_stale`，但全机支架扫描在第7/12阶段返程中因VINS加速度bias越线而中止。未进入释放后N05准入或无目标悬停。连续计数由#170后的1/3重置为0/3；N07仍`in_progress`。

## 运行与门禁

- Run：`n07-20261024-171-01`；epoch `58e155bf564f4671bd613d0277585291`。
- 镜像：`sha256:099ab9afecd28b7354f6d6494944b1db30c7c67c973e9b93b03f87aca7ad6f8`；runtime contract SHA-256：`856bf1f2222a5286493813c9702731f7e5166844eb2bfd98c6f525f3f36924eb`。
- 布局／profile／spawn：`wall_box_column`、`n06_full_airframe_retreat_240_oblique_early_view`、`-6.5,0,0.3,0,0,0`，与#170相同。
- 启动只读探针运行45.018墙钟秒；localization于2.761秒进入TRACKING。telemetry最大仿真源龄0.080秒，source gap P95为0.068秒；窗口内没有`telemetry_stale`。
- 初始N05只读检查拒绝`ground_plane_insufficient_raw_occupied_voxels`。未绕过该门，也未把raw unknown转成free。

## 失败证据

扫描运行341.394墙钟秒后完成阶段0–6，失败发生在`leg_index=7`返程段，机体从远端向起点平移。完整`fixture-vins.jsonl`显示`accel_bias_norm`于仿真时间277.300秒首次越过配置中的0.15 m/s²运行健康界（0.150982），之后持续上升至0.189144；`fixture-trace.jsonl`在277.420秒仍记录TRACKING样本，随后fixture终态报告锁存`accel_bias_norm_exceeded`。这是支架扫描期间的bias健康失败，不是启动期输入过期的复现。

#170采用相同镜像、profile和路线完成12/12；其扫描VINS诊断记录最大`accel_bias_norm=0.080401`。这证明两个epoch结果不同，但尚不能说明#171 bias上升的上游原因。健康门保持原值，没有代码、配置或运行参数改动。

## 安全收尾与范围

没有`n05-prescan-ready` return-pose marker，因此没有attached/released gate、飞行或hover结果。runner回执确认支架detached，Gazebo确认fixture模型不存在；PX4状态为DISARMED，land detector为landed，桥状态为DISABLED/unarmed/landed。项目停止命令`bash tools/project.sh stop n07-20261024-171-01`成功，容器退出码0，无活动项目容器。

## 产物

- 完整原始数据：[`artifacts/runs/n07-20261024-171-01/`](../../artifacts/runs/n07-20261024-171-01/)
- 关键文件：`n05-run-inputs.json`、`runtime-contract.json`、`n05-before/n05-live-entry-check.json`、`n07-vio-stream-diagnostic.json`、`fixture-result.json`、`fixture-stages.json`、`fixture-trace.jsonl`、`fixture-vins.jsonl`、`failure-safety-readback.log`。
- 运行结果 SHA-256 登记于[JSON报告](n07-support-scan-health-failure-20261024-171.json)。

## 后续

#172使用同一固定方案进行新的独立冷启动，完整保留bias时序以判断越线是否复现。若相同返程段再次触发越线，停止盲目重复并转根因分析；若通过扫描和释放gate，才继续N07无目标悬停。N07其余门限不变。
