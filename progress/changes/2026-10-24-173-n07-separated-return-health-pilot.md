# N07.19 #173：缩短斜视暴露的独立路线复核

## 执行模式与范围

Goal 完成模式；用户指定范围N07，父目标保持`in_progress`。#171与#172在原`oblique_early_view` profile相同返程阶段复现bias越线；当前连续合格次数0/3。

## 证据与假设

失败运行在stage6（pitch 0.45→0）前后已积累bias：#171由0.054637增至0.086980，#172由0.057167增至0.117803；随后均于stage7返程平移时越过0.15 m/s²。#170同路径stage6最大0.060414、stage7最大0.064936并通过。#166也在stage7失败；#165/#167/#168通过。VINS features、long tracks与solver仍可用，当前证据未指向telemetry stale或计算超限。

假设：约130秒的0.45-rad oblique view并紧接pitch归零和return translation，增加了跨epoch VINS accelerometer bias越线概率。既有`n06_full_airframe_retreat_240_oblique_separated_return`将pitch暴露缩为约30秒，历史#138 wall/#148 corridor均完成12/12，最大bias分别0.085480/0.076170；#138发生在#142相机安装坐标修复之前，N05 raw-ground拒绝不能代表当前组合。

## 唯一变量与判据

固定镜像、runtime、world、spawn、wall layout、EKF2、健康门、N05 gate和no-goal hover程序；唯一主要变化为采用既有`oblique_separated_return`扫描profile。若完整12/12且attached/released online/offline gates一致接受，才继续N07 no-goal hover；若健康失败或release gate拒绝，安全清理后停止，不绕过gate、不启动飞行。该项用于验证route-level假设，不降低健康阈值。

## 完成标准

完整支持扫描、安全拆架、fresh N05 release admission及N07全部出口。仅通过支持路线不计N07 hover次数；N07成功run仍须至少30仿真秒no-goal hover、独立定位／PX4时序、EV融合且无GNSS/GPS aiding、唯一控制发布者／无真值节点及最终landed/disarmed。

## 结果

#173的路线假设在bias维度获得支持：新epoch使用`oblique_separated_return`，支架12/12回到起点；全程VINS `accel_bias_norm`峰值0.083839，未越过0.15 m/s²，VINS solver保持usable。初始N05 online/offline仍一致拒绝raw unknown，没有绕过。

但是attached和released N05 live gate都在原120秒等待后以`missing=['odom']`失败。Localization已锁存`telemetry_stale`，桥为DISABLED。失败时status的source stamp停在sim 386.136，而clock已到487.572；post-release只读回读时raw VINS telemetry已更新至555.292、raw odometry至556.744，但adapter status仍锁存旧source stamp且不再发布optimized odom。项目的health状态为fail-closed、无同epoch解锁路径；不能以raw源恢复替代adapter odom或N05正向准入。

支架已detach并确认Gazebo模型移除，PX4 DISARMED、landed；项目stop成功，容器exit0。未进入release gate通过、flight或hover。本run不计入N07连续次数，仍0/3。详细时序和局限见[证据报告](../evidence/n07-support-scan-telemetry-stale-20261024-173.md)。下一步#174保持同一路线和门限，启动read-only freshness probe贯穿扫描与attached检查，区分raw VINS输入间隔与adapter optimized-odom停发；只有fresh N05 gates通过才运行hover。
