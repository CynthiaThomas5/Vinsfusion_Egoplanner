# N07.15 #169：连续悬停序列第 3/3 次复现

## 执行模式与范围

Goal 完成模式；用户指定 N07。当前连续合格 no-goal hover为2/3（#167、#168）。本子项在同固定版本执行第三个独立冷启动；只有所有准入、实际融合、独立评估、健康／时间域和落地上锁出口均通过，N07才可标 passed。

## 已有基础与判据

#167与#168均使用镜像`sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`、runtime契约`856bf1f2222a5286493813c9702731f7e5166844eb2bfd98c6f525f3f36924eb`、spawn `(-6.5,0,0.3,0,0,0)`、wall场景和`n06_full_airframe_retreat_240_oblique_early_view`；均完成12/12支架阶段、attached/released N05五阶段online/offline一致接受，再完成同epoch≥30秒 no-goal hover、真实EV融合、无GNSS/真值辅助、唯一bridge控制publisher、独立误差、连续健康与 landed/disarmed。两次fixture runner错误均保留，独立N05和N07评估通过。

Run `n07-20261024-169-01` 复用完全相同的配置、route、N05/健康门、PX4参数和hover程序；唯一主要变化为fresh simulation epoch。先完成完整支架路线和attached/released fresh gate；仅released gate全过后进入≥30仿真秒no-goal hover。保存失败或中断结果，门限不变。全出口通过后连续计数3/3并审核N07状态；失败则按原文重新计算连续次数。

## 结果

失败，未进入 N05 支架准入。Run `n07-20261024-169-01` 使用与 #167/#168 相同的固定镜像、runtime、spawn、wall layout、支架route和健康／N05门限；fresh epoch 为 `909adf46d6044c4d9d4b709e094ef04e`。初始只读 N05 检查以 `--wait-s 150` 等待后仍缺少 `/localization/optimized_imu_odom`，收到 bridge、clock、localization、map，fail closed 为 `online_snapshot_or_prerequisite_check_failed`。`n05-prescan-ready.json` 与 `fixture-result.json` 均未生成，故没有支架扫描、attached/released gate、目标或飞行。

只读 ROS 状态回读为 localization `state=4`、`valid=false`、`reason=telemetry_stale`、`good_pairs=84`、`accepted_optimized=75`、`accepted_propagated=1227`、最后适配器传播源戳 `13.980 s`；同一 epoch 的 bridge 为 `DISABLED`、`armed=false`、`landed=true`、控制关闭。之后 raw VINS telemetry 与 odometry 仍可读到新源戳，但不能解除健康锁存或补回适配器里程计。未观察到解除或重启机制；没有更改健康阈值。这里记录的是失效表现，具体导致 telemetry 过期的上游调度根因仍未判明。

容器按 `bash tools/project.sh stop n07-20261024-169-01` 停止，Docker 状态 `exited`、退出码0；运行期间没有 fixture、目标或控制发布。按 N07 连续三次且失败后重算的出口，#167/#168保留为独立通过证据，但当前连续合格计数重置为 **0/3**。失败证据与日志见[报告](../evidence/n07-preflight-health-failure-20261024-169.md)及 `artifacts/runs/n07-20261024-169-01/`。下一子项 #170 在不改配置和门限的前提下重新冷启动；同一偶发失效模式在 #090 与本次均有观测，因此记录启动期 telemetry/adapter 状态以区分复现与恢复，不将 raw VINS 仍发布误当成准入通过。
