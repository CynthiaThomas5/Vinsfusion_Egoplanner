# #160 N07 保持 yaw 视角返程结果

run `n07-20261023-160-01` 使用 spawn `(-6.5,0,0.3)` 与1.8m后退路线。初始 fresh N05 因`ground_plane_insufficient_raw_occupied_voxels`拒绝；独立 offline replay 同样拒绝，未解锁。

## 扫描结果

9阶段profile完成阶段0–4。返程阶段5在sim 183.284s触发`normalized_cost_exceeded`；最后有效fixture trace在sim 183.364s、x≈−1.376m、yaw≈+0.15rad，记录cost=0.470874，随后latched status cost=1.021007。epoch保持单一。

- 返程窗口229条VINS记录：long tracks最低120、stereo features最低149、加速度bias最高0.051767m/s²。全程bias峰值0.086773m/s²。这次没有复现#159的低long-track或近0.15m/s² bias。
- 因定位锁存，profile未完成，也没有`n05-prescan-ready.json`或扫描后的attached/released fresh N05结果。初始门拒绝原因与离线复算相符。

## 安全状态

fixture helper执行清理并确认detach；remove service已确认，Gazebo model list中无fixture，`fixture_may_remain_attached=false`。PX4状态样本均为DISARMED。独立状态查询为bridge `DISABLED`、control disabled、armed=false、landed=true；定位无效。执行`bash tools/project.sh stop n07-20261023-160-01`后容器Exited(0)。未解锁或飞行，N07 hover仍0/3。

## 解释与下一步

#159和#160均在返程约x=−1.4m附近锁存；但#160返程跟踪和bias仍健康，因此目前不能把故障归因于yaw视角造成特征不足。#161保持1.8m平移、yaw=0、spawn、布局和所有健康／N05门限，仅在远端试+0.45rad向下俯仰观察，再在返程前复位pitch=0。目标是增加对起飞包络内地面边界上方或与边界相交的raw unknown的观测；whole-cell低于raw-ground plane的格子仍由现行N05规则排除。

机器可读摘要：[n07-retreat-observation-20261023-160.json](n07-retreat-observation-20261023-160.json)。静态路线：[geometry JSON](n07-retreat-180-yaw015rad-return-geometry-20261023-160.json)。运行日志与哈希位于`artifacts/runs/n07-20261023-160-01/`。
