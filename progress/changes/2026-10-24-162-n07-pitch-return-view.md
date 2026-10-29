# #162 N07 俯视保持到返程结束

对话摘要：[N07 俯视保持到返程结束](../../collaboration/dialogues/2026-10-24-162-n07-pitch-return-view.md)

## 父目标、子项与依据

执行模式：Goal完成模式；用户指定范围N07。父N07=`in_progress`，当前子项N07.8 #162。#161在远端pitch观察、复位后返程时触发normalized-cost锁存；pitch各观察阶段仍健康，返程在x≈−1.592m锁存。假设保留俯视到home，可减少返程时切回水平视野造成的纹理变化。

## 唯一主要变量与修改

与#161使用同一1.8m x路线、pitch幅值+0.45rad、远端15s保持、yaw=0、spawn、布局、raw分类和健康门限；仅将pitch reset从返程前移至x=0返程完成后。9阶段时长总和保持不变。静态全机参考球几何路径与#161相同，继续使用[路线报告](../evidence/n07-retreat-180-pitch045-route-geometry-20261024-161.md)，未修改地面或飞行包络规则。

## 安全状态证据补齐

将`VehicleLandDetected`加入支架探针订阅；fixture移除后额外等待1仿真秒并记录最新landed值和接收龄。`run_n05_preflight_layout.sh`若支架未移除或探针未确认fresh landed=true，则保留运行容器供监护。N07用手动同容器流程，使released gate通过后可在原冷启动继续悬停；入口拒绝则按项目停止流程结束，不创建新epoch拼接。

## 结果

新 run `n07-20261024-162-01` 初始 fresh N05 online/offline 完全一致，但拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`。raw-ground plane 为 z=-0.35m。入口检查分别报告 TAKEOFF_CONTACT 436、ASCENT/DESCENT 592、HOLD 566 个未知体素；另有 TAKEOFF_CONTACT 44 个 whole-cell subground voxels 被排除。独立 [unknown-volume audit](../evidence/n07-n05-unknown-volume-audit-20261024-162.json) 复算 HOLD 的566个未知体素中心均高于地面（z=0.45..1.25m）；TAKEOFF_CONTACT 的436个未知中心里0个低于地面、52个在平面、384个高于平面。因此拒绝不是把地面以下作为飞行空间。

profile 在第3/9阶段 pitch 转入中止。最后健康 fixture trace 为 sim=148.744s、pitch target=+0.201rad、actual=+0.193rad；状态报告锁存 `normalized_cost_exceeded=1.138230`。883条捕获 telemetry 按同一公式重算最高0.694196；最少 long_tracks=56、stereo_features=126、最大 accel bias=0.10082m/s²，均未越当前健康门。探针没有逐事件保存 `LocalizationStatus`，因此产生1.138230的确切 telemetry 样本未确定。没有attached后或post-release N05检查，也没有hover。

fixture完成detach并从Gazebo模型列表确认移除；135条LandDetected记录均true，最后一条接收龄约0.303s且验证通过；PX4样本均DISARMED。独立查询确认bridge DISABLED、无控制、未解锁、landed=true、定位无效。只停止该run，容器Exited(0)。详见[#162证据报告](../evidence/n07-retreat-observation-20261024-162.md)。

## 下一子项

N07.9 #163 对#162完全相同的profile做一次有界复现，唯一新增诊断是完整记录每次 `/localization/status` 事件，确认cost锁存是否由短时telemetry尖峰触发。N05与定位健康门限不变；如9阶段完整，立刻在同一epoch检查attached、released及post-release fresh N05，online/offline必须一致全通过才可转入N07悬停。
