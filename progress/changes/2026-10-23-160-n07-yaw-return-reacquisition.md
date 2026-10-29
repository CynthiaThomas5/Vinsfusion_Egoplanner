# #160 N07 保持 yaw 视角返程

对话摘要：[N07 yaw 视角保持返程](../../collaboration/dialogues/2026-10-23-160-n07-yaw-return-reacquisition.md)

## 父目标、子项与依据

执行模式：Goal 完成模式；指定范围 N07。父 N07 保持 `in_progress`，当前子项 N07.6 #160。#159 的+0.15rad yaw转入、15s保持及远端复位期间健康；随后 yaw=0返程时 long tracks 降至45，并触发 `normalized_cost_exceeded`。假设保留+0.15rad到x返程完成，可减少视觉视角复位对返程跟踪的影响。主要变量仅为 yaw 复位时机；translation、pitch、spawn、布局、N05和health门限保持不变。

## 计划与边界

- run `n07-20261023-160-01`，保持最大后退1.8m。
- 远端 yaw 转到+0.15rad、保持15s，然后在 yaw不变时沿原路径返程；原点处独立复位 yaw=0，随后按原配置下降。
- static geometry先确认全机包络净空；运行前通过profile回归和shell/JSON检查。
- 仅DISARMED支架扫描与N05准入。定位、epoch、fixture释放、freshness、身份任一失败则不解锁。Released N05五阶段 online/offline通过后，才可在同一冷启动做首个30s无目标悬停。

## 静态路线

X支架关节相对world-anchored base，yaw支架关节位于其下游；因此保持yaw返程仍沿用#159相同的world-x中心线。按orientation-invariant全机参考球核查25个静态障碍，1cm采样，最小连续非地面下界0.889410m。报告：[geometry JSON](../evidence/n07-retreat-180-yaw015rad-return-geometry-20261023-160.json)、[说明](../evidence/n07-retreat-180-yaw015rad-return-geometry-20261023-160.md)。支架自身、定位、地图和制动不在该静态证明范围内。

## 结果

- 配置／runner回归：`python3 tools/test_preflight_scan.py`，25 passed；`python3 -m json.tool config/components/simulation/preflight_scan.json` 和 `bash -n tools/run_n05_preflight_layout.sh` 通过。
- run `n07-20261023-160-01`：9阶段profile仅完成0–4；返程阶段5在sim 183.284s因`normalized_cost_exceeded`关闭mapping gate。最后有效trace sim 183.364s、x≈−1.376m、yaw≈+0.15rad、normalized cost=0.470874（status快照值）；随后锁存status cost=1.021007。VINS返程窗口229条，long tracks最低120、stereo features最低149、accel bias最高0.051767m/s²；因此未复现#159的long-track低值或近门限bias。epoch唯一且扫描阶段未显示epoch切换。
- 初始N05拒绝`ground_plane_insufficient_raw_occupied_voxels`；离线独立复算与在线结果匹配。定位锁存早于`n05-prescan-ready.json`，没有attached/released post-scan门控结果。
- helper安全清理确认fixture detached、remove service ack、Gazebo model absent；PX4状态样本均为DISARMED。独立查询确认bridge DISABLED、control disabled、armed=false、landed=true；随后`bash tools/project.sh stop n07-20261023-160-01`，容器Exited(0)。未解锁、未飞行，N07 hover仍0/3。
- 运行证据：[报告](../evidence/n07-retreat-observation-20261023-160.md)、[JSON](../evidence/n07-retreat-observation-20261023-160.json)、[初始N05离线复算](../evidence/n07-n05-before-offline-replay-20261023-160.json)。

## 下一子项

#159/#160的两种yaw时序均在返程约x=−1.4m处锁存；#160的VINS跟踪和bias仍健康，故目前不能归因为“yaw复位造成特征丢失”。#161保持x/yaw/spawn/场景/健康门限，单独加入远端+0.45rad俯视观察并在返程前复位pitch=0，测试相机视场能否补到takeoff附近、地面边界上方的raw unknown。+0.45rad为此前支架扫描使用过的俯视方向；#138的相机安装尚未修正，不能把其N05结果当作本轮准入证据。
