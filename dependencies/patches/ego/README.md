# EGO补丁

来源：https://github.com/ZJU-FAST-Lab/ego-planner-swarm ，commit `23a8d5a191711dd65633df689bd00f55d4dea8f9`，GPL-3.0-only；只物化5个规划包。

有效顺序：0001–0011 → 0017 → 0018 → 0019 → 0021 → 0035 → 0036。具体应用根目录与strip见`dependencies/sources.json`；0036用binary模式保留原CRLF，重放不重写无关源码。

0035保留起始航向边界；0036对停止目标固定三次B样条末3控制点，约束终点、末速度和末加速度；非停止局部目标仍用原优化方式，碰撞／可行性检查保留。未纳入的unknown／扫掠／诊断候选不代表已解决，正式安全条款仍待验收。

补丁哈希、上游许可哈希、基准构建及当前验证范围分别记录在依赖清单和progress证据。

0037在同一基准提交、0036之后应用（src目录，-p1，GPL-3.0-only）：新增只读`/mapping/query_occupancy_sphere`；复用0021的epoch／map_id／融合新鲜度门，直接统计与闭球相交的raw体素，不用inflation mask代替unknown，也不修改地图／规划／求解器。单次半径≤2m、包围盒≤100000格是资源上限。查询及0021共享新鲜度检查；补丁和三个最终文件哈希锁在sources.json。#062记录17包构建、fresh fetch及不解锁验证；不构成轨迹或飞行安全通过。

0040在同一基准提交、0039之后应用（src目录，-p1，GPL-3.0-only）：增加只读`/mapping/depth_fusion_trace`，按当前epoch/map_id记录plan_env同步深度／位姿回调和射线投影、占据更新完成的仿真时间与steady-clock时间、源戳及计数；reset时清零计数并记录新身份。它只增加诊断发布，不改变输入、地图、规划或控制行为。补丁与`grid_map.cpp`／`grid_map.h`结果哈希锁在sources.json。17包构建、223项回归、三次idle epoch和当前版深度断流／reset验证见[#090 N03证据](../../progress/evidence/n03-depth-fusion-continuity-20261022-090.md)。

0041在同一基准提交、0040之后应用（src目录，-p1，binary重放保留advanced_param.launch.py的CRLF，GPL-3.0-only）：EGO最终曲线检查使用映射配置中与N05 body-reference clearance一致的raw occupancy sphere；每条终端／紧急停止曲线还检查N05配置的0.25 m hold neighborhood，开始与结束都复核身份和融合新鲜度。配置缺失或曲线／保持区查询异常时拒绝，记录查询数量与steady-clock检查耗时。它不发布PX4控制，也不授权飞行；SITL布局和地图证据见N06进度报告。
