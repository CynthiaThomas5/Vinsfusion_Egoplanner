# N07.7 #161：远端俯视观察

## 依据

#158的1.8m后退路线VINS健康，但fresh released N05仍有TAKEOFF unknown（格子中心在raw-ground边界上或其上方）及3个HOLD unknown。#159/#160的yaw变体在返程约x=−1.4m锁存；#160该段long tracks最低120、加速度bias最高0.05177m/s²，当前没有证据说明yaw改变导致了视觉跟踪不足。

## 决定

只测试远端+0.45rad向下pitch观察，yaw保持0；观察15秒后独立复位pitch，再返程。后退距离1.8m、spawn、场景、raw分类规则、N05阈值和健康门限不变。依据D435i SDF水平视场与640×480比例，垂直视场约70.9°。预期观察対象是TAKEOFF/HOLD包络内地面边界上或其上的raw unknown；whole-cell低于地面边界仍按现行N05排除。

## 验收

先完成静态全机包络路线报告和profile回归。冷启动run `n07-20261024-161-01`仅做DISARMED扫描。扫描后需attached和released fresh N05五阶段在线门与独立离线复算一致；不满足时保持不解锁。只有released gate全部通过，才在同一启动核对EKF2 EV fusion、无GNSS/真值、唯一控制publisher并开始≥30仿真秒无目标悬停。

## 结果与下一步

run `n07-20261024-161-01`完成0–5阶段；远端pitch转入、15秒保持和复位期间定位有效，返程阶段6从sim162.02s开始，在sim184.108s因`normalized_cost_exceeded`锁存，位置x≈−1.592m，返程未完成。门关闭时的157条VINS telemetry记录long tracks最低97、stereo features最低147、bias最高0.07137m/s²；全run bias峰值0.13677m/s²。锁存status cost=1.08510；返程trace后续读到的是旧valid status。门关闭后清理期间VINS norm最高1.21109、long tracks126，不能把本次归因于低特征数。初始N05因raw-ground候选0拒绝，离线回放相同；未形成ready marker和post-scan gate。helper回到home支架位、detach并移除模型；PX4样本DISARMED，容器Exited(0)，未飞行。恢复后PX4 LandDetected未被探针采集，限制已记录。详见[报告](../../progress/evidence/n07-retreat-observation-20261024-161.md)。

下一项#162只改变pitch复位时机：+0.45rad保持到x=0返程完成，再复位pitch=0。目标是持续观察地面边界附近纹理；未通过fresh released N05仍不解锁。
