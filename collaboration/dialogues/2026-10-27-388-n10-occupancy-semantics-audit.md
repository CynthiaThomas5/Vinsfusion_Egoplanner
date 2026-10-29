# 2026-10-27-388 N10 occupancy 语义审计

## 摘要

用户此前授权继续完成 N10。本轮核对 #385 箱体内部 raw occupancy 查询为何在注入后仍为 free，并检查 EGO 原生 inflated collision 语义。无 PX4/Gazebo 运行，无飞行。

## 确认

- #385 的查询球完全位于 SDF 箱体内部，离 x 负向迎机表面约 0.272 m，没有采到表面。
- `/mapping/query_occupancy_sphere` 查询 raw cells；native EGO optimizer 与 collision callback 检查 inflated occupancy。相机射线写入可见端点及其前方自由射线，不会把实体内部全部填成 occupied。
- 归档没有直接保存箱体表面点坐标或同时间的 inflated point query。故能解释内部 raw query 可能为 free，但不能证明当时表面已观测／膨胀或因其触发重规划。

## 决定与待办

N10.3/#388 只读审计已记录。下一项 #389 评估现有归档并准备只读表面与内部查询观察，保留 frame/source/fusion stamp、epoch/map identity 和 occupied 点坐标，不新增运行拒绝门。N10.3/N10 尚未通过。
