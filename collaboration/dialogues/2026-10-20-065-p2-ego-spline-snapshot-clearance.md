# GOAL C B-spline 同 stamp 占据快照 #316

用户继续推进 GOAL C，保持 P0–P6 单 D435i 仿真导航范围。沿用 #315 的隔离 EGO binary 和 patch 0028；只改 run-local 观测器，在收到每个唯一 B-spline 后异步请求已有只读 `GetOccupancySnapshot`，再离线重建曲线并按 plan_env 栅格规则采样。没有修改 canonical dependencies 或 `src/vendor`。

#316 收到3条不同轨迹ID的 B-spline，并取回3份 epoch/map_id匹配的 240×240×60 快照。服务 stamp 对轨迹 start_time 分别晚1 ms、相等、相等；融合深度源龄99–110 ms。10 ms曲线样本均在地图内，raw occupancy均为known-free。轨迹2、3分别有10、6个采样落入 EGO 0.5 m inflation mask；代表地图中的 known voxel 仅0.59–0.62%，最近 occupied voxel box距离0.512 m，仅比既有0.482 m名义球包络大约30 mm。静态源码显示 inflation mask 是按各轴 ±5 voxels 的立方体扩张，不能把 mask 命中直接解释成球体碰撞；同样不能因中心线到voxel box距离较大就确认真实净空。

决定：只记录为近时刻地图 overlay 诊断；样条未执行，也没有完整覆盖、真实表面误差、扫掠体积或PX4证据，GOAL C/D/F仍pending。下一步核对优化器的碰撞采样与立方体膨胀之间的差异，再以独立epoch和障碍布局重复采集。
