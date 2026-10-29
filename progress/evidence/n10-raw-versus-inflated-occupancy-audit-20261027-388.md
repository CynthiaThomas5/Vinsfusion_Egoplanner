# N10.3/#388 Raw occupancy 与 inflated collision 语义审计

**结论：** #385 方箱内部查询检查的是 raw occupancy 球体，不是方箱迎机表面；`free=160` 本身不能证明表面漏检或官方碰撞层失效。现有归档没有箱体表面 occupied 点坐标，也没有同时间的 inflated 点查询，所以动态障碍因果仍未确认。本项仅审计源码和已有 #385 记录，没有改运行策略或启动仿真。

## 为什么箱体内部查询会是 free

#385 的固定变换把 SDF 箱体中心映射到 world `0.000, 0.000, 1.400 m`；尺寸为 `0.8×0.8×2.8 m`。箱体 x 负向表面位于 `-0.400 m`。归档的两次注入后查询都以 world `0.122, -0.001, 1.166 m` 为中心、半径 `0.25 m`；球体 x 负向边缘是 `-0.128 m`，距可见前表面 `0.272 m`。因此查询球完全在箱体内部，没有覆盖前表面。

两次同一 map identity 的 raw query（sim `69.64` s 和 `70.40` s）均返回 `free=160, unknown=0, occupied=0`。服务 `/mapping/query_occupancy_sphere` 统计球体相交的 raw `occupancy_buffer_` cells；它不查询膨胀层。源码中相机射线把返回点之前的格子记为 free，把有效深度返回端点记为 occupied；它不会把实际箱体内部体积全部填成 occupied。动态生成实体后，内部格子保留先前自由观测是可能的，所以内部 raw 查询不能替代前表面观测。

## EGO 实际碰撞使用的层

活动 `official_ego` 规则下，`getInflateOccupancy` 读取 `occupancy_buffer_inflate_`；原生优化器和 0.01 s 轨迹碰撞回调也使用该谓词。只读 `/mapping/query_planning_occupancy` 端点可查询这个上游点谓词，要求 `radius=0`，并会返回查询点、frame、时间戳和 map identity；它不控制飞机。地图就绪保留 epoch/map、fused depth/pose 状态检查，但项目本地 source-age 拒绝已由 patch 0054 删除；EGO 自带 odom/depth 超时仍然存在。

## 归档能与不能证明的事

- #385 时间戳 READY `PositionCommand` 的中心线距箱体至少 1.463 m；真值全机包络采样扣除最大样本间运动后为 1.131 m，且禁碰接触数为 0。这是该次采样净空，不是连续净空证明。
- 归档没有箱体前表面的 raw occupied 点坐标，也没有同时刻 `/mapping/query_planning_occupancy` 读回。已有 occupied ROI 计数属于另一场静态圆柱观察，不能当成箱体点证据。
- 所以源码语义解释了为什么“箱体内部 raw query=free”不必然表示错误，但不能证明 #385 的箱体表面被看到、进入 inflated 层或触发了绕行。动态障碍因果证据仍缺。

## 下一项

N10.3/#389 准备只读观测：把请求点分别放在箱体前表面、前表面外侧和内部；同步保存 raw sphere 结果、inflated point 结果、返回 frame/source/fusion stamp、epoch/map id 和实际 occupied 点坐标。先检查可复用归档；若必须重现，运行时只记录和查询，不增加新的拒飞门。此状态查询期间没有启动新飞行。

机器报告：[JSON](n10-raw-versus-inflated-occupancy-audit-20261027-388.json)。源码：[raw 查询和 readiness](../../src/vendor/ego_planner/planner/plan_env/src/grid_map.cpp#L18)、[sphere query](../../src/vendor/ego_planner/planner/plan_env/include/plan_env/sphere_query.h#L15)、[inflated predicate](../../src/vendor/ego_planner/planner/plan_env/include/plan_env/grid_map.h#L392)、[原生轨迹碰撞检查](../../src/vendor/ego_planner/planner/plan_manage/src/ego_replan_fsm.cpp#L1013)。
