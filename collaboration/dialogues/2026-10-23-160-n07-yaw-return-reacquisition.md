# N07.6 #160：保持 yaw 视角返程

## 假设

#159的+0.15rad转入、保持和远端复位期间定位有效；复位 yaw=0 后，返程 long tracks最低45并触发normalized-cost锁存。保持+0.15rad完成x返程，可能减少返程前的视角变化，保留相同特征跟踪。

## 唯一变量

将 yaw复位从远端移到x=0原点。仍然先在远端看+0.15rad，保持15秒；然后yaw不变沿相同x路径返回，最后在起点yaw单独复位。平移距离1.8m、pitch=0、阶段主要时长、runtime spawn、布局、N05和health门限不变。

## 验收

所有扫描阶段VINS健康且epoch连续、PX4 DISARMED、fixture已移除；fresh released N05五阶段online/offline全部通过后才执行悬停。未通过则继续fail-closed，不解锁。

## 结果与决定

run `n07-20261023-160-01` 完成profile前5阶段；返程x≈−1.38m时VINS以`normalized_cost_exceeded`锁存。返程229条VINS记录的long tracks最低120、stereo features最低149、accel bias最高0.05177m/s²，未复现#159的低long-track或近门限bias。初始N05因`ground_plane_insufficient_raw_occupied_voxels`拒绝，独立offline replay与online相同；定位失败前没有完成扫描后的attached/released gate。helper确认支架脱离并移除；PX4 DISARMED、bridge DISABLED、control disabled、landed=true，项目容器Exited(0)。无解锁／飞行，N07仍0/3。

结果摘要与哈希：[n07-retreat-observation-20261023-160](../../progress/evidence/n07-retreat-observation-20261023-160.md)。两次yaw路线均在返程约−1.4m锁存，但#160跟踪/bias正常，暂不能归因于yaw复位。下一项#161在同样的1.8m路径单独试远端+0.45rad俯视观察，返程前复位pitch=0；观测目标是起飞包络内raw unknown中地面边界上方或与边界相交的格子。地面以下整格继续由N05现行规则排除。
