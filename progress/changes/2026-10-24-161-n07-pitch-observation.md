# #161 N07 远端俯视观察

对话摘要：[N07 远端俯视观察](../../collaboration/dialogues/2026-10-24-161-n07-pitch-observation.md)

## 父目标、子项和依据

执行模式：Goal 完成模式；用户指定范围N07。父N07=`in_progress`，当前子项N07.7 #161。#159/#160加入远端yaw视角后均在返程约x=−1.4m锁存；#160返程long tracks≥120、accel bias≤0.052m/s²，故暂不能归因于yaw期间特征丢失。#158的raw-map审计已显示TAKEOFF未知体素位于ground-plane边界上或其上方，HOLD还有高处unknown；whole-cell低于fresh raw-ground plane的格子不计入飞行体积。

## 单变量假设和边界

假设：当前相机水平视场在pitch=0时未覆盖起点附近地面边界上方的部分包络；远端pitch=+0.45rad（此前支架扫描使用的向下观察方向）可增加这些体素的raw观测。唯一主要变量为远端俯仰观察，保持x路线、yaw、spawn、场景、N05策略与健康门限不变。profile阶段为`[3,12,100,10,15,10,100,15,5]`秒；相机pitch reset与x返程分开。

- 新增`n07_spawn_minus65_retreat_180_pitch045_view`，注册fixture runner与N05 layout shell入口，并加入profile回归。N05 runner的安全续检条件现按所选profile阶段数计算，避免将完整的9阶段N07路线误判为未完成12阶段coverage profile。
- 静态路线使用25个障碍、全机参考球半径0.730618m、1cm采样，连续非地面净空下界0.889410m；报告：[geometry JSON](../evidence/n07-retreat-180-pitch045-route-geometry-20261024-161.json)与[说明](../evidence/n07-retreat-180-pitch045-route-geometry-20261024-161.md)。
- 开工回归：`python3 tools/test_preflight_scan.py` 26 passed；preflight JSON parse、`bash -n tools/run_n05_preflight_layout.sh`及`git diff --check`通过。

## SITL 边界与验收

run `n07-20261024-161-01`只做DISARMED支架扫描。起始N05门可以拒绝但必须记录；扫描完整且定位/epoch连续后依次取得attached、released fresh N05结果和独立离线回放。released五阶段未全部accept且online/offline不一致时不启用bridge、不解锁、不悬停。若五阶段全通过，才在同一冷启动完成EKF2 EV融合／无GNSS与真值／唯一控制publisher检查，并开始N07首轮≥30仿真秒无目标悬停。

## 结果

- run `n07-20261024-161-01`：9阶段profile完成0–5，pitch转入、15s保持、复位均valid，实际pitch峰值+0.46299rad。x返程从sim162.02s开始，在sim184.108s首次关闭mapping gate：`normalized_cost_exceeded`。返程仅到x=−1.592m；helper回到home支架位后安全detach并删除fixture，PX4所有状态样本DISARMED，项目容器Exited(0)。
- 返程到gate关闭的157条VINS记录long tracks最低97、stereo features最低147、accel bias最高0.07137m/s²；全run bias峰值0.13677m/s²。锁存status cost=1.08510；fixture trace在关闭后还保留旧valid status，不作为恢复证据。VINS telemetry在错误清理期间norm cost最高1.21109，long tracks=126，因此没有证据表明这次cost越线源自低特征数。
- 初始N05拒绝`ground_plane_insufficient_raw_occupied_voxels`，candidate count=0；独立离线复算与在线相同。没有prescan-ready marker或扫描后的attached/released gate，pitch视角对unknown体素的影响未知。未起飞，N07 hover=0/3。
- 安全记录确认fixture detached/remove ack/model absent、PX4 DISARMED；恢复后land detector样本未被该版探针记录。初始检查为landed=true，车辆由支架返回home地面位后脱离；该限制单独保留。
- 结果：[报告](../evidence/n07-retreat-observation-20261024-161.md)、[JSON](../evidence/n07-retreat-observation-20261024-161.json)、[初始N05离线复算](../evidence/n07-n05-before-offline-replay-20261024-161.json)。

## 下一子项

#162将+0.45rad保持到x=0返程结束，再于home复位pitch。唯一变量为复位时机；x路线、保持时长、yaw、spawn、布局、N05与health门限不变。假设返程时持续观察地面边界附近纹理可避免pitch复位后视野变化导致的cost lock。#160已表明只保持yaw+0.15rad返程仍锁存；本轮改为俯仰持续观察，是新的单变量候选而非降低健康阈值。
