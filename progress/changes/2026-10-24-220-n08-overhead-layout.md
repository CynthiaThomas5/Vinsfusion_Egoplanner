# N08.2j #220：N08 专用顶板回波布局

## 假设、唯一变量与判据

- 假设：原 EGO sphere 上方扇区未知，是因为导航 world 没有有限的 overhead 深度回波面；在真实 SITL 场景加入静态碰撞／视觉顶板后，传感器射线可把顶板下方体素标为 raw free，同时顶板表面仍是 raw occupied。
- 本轮唯一环境变量：使用 N08 专用 `n08_overhead_calibration` 布局，含 8×8 m、底面 z=2.65 m 的真实箱形顶板。其余采用 #218 的 −0.45 rad 观察姿态、原 N05 路线、planner 半径、N05／N06 和 unknown 门限。
- 判据：同 epoch/map 的 N05 post-release gate online/offline 一致通过；从 N05 hold center 到 actual same-run odometry start 的原半径 EGO sphere 以及目标／完整曲线需要的 clearance 查询全 free；实际顶板单元应按 raw occupied 被识别。任一项未满足，不启动 compute-only；无独立停止边界前不执行 XY。

## 范围与产物

- 新配置：`config/components/simulation/n08_overhead_calibration.json`。
- 最小接线：N05 支架工具可加载该独立布局，记录配置来源／哈希及生成模型；不更改 N04 已验收 layout、N05/N06几何／门限、占据语义、定位、PX4 或 N07 标准。
- 静态核验：JSON、Python AST/profile/joint bounds、shell syntax、生成 SDF 与 project status。
- 运行核验：N05 same-run support scan + online/offline post-release admission；仅当上述地图条件全过才进入隔离 bridge 的 compute-only。
- 下一步：地图通过时做 #221 compute-only 轨迹／停止包络核对；地图不通过则记录 raw-cell 原因并继续修复场景可观测性，不执行飞行。

## 安全几何说明

顶板作为真实碰撞物加入 Gazebo，尺寸 8×8×0.1 m，中心在 spawn 上方，底面 z=2.65 m；相对标称起飞高度与 body sphere 加 0.25 m terminal-hold 查询，名义余量约 0.4 m。该余量仅用于设计审计，不作为飞行证据；地图仍须以 D435i raw rays 证明净空，顶板接触格必须保持 occupied。

## 首次运行结果

- #220 的 N08 layout 实际只含 ceiling，未包含 #218 `wall_box_column` 里的 `n04_box`／`n04_column`，因此场景差异不止顶板；这个对照不用于归因。
- `gz sdf -k` 对生成顶板模型报告 `Valid`。模型中心 pose `[-6.5,0,2.7]`、尺寸 `[8,8,0.1]` m、底面 z=2.65 m。
- 支架扫描在 6/15 stages 后因 localization `normalized_cost_exceeded`（1.029）中止；无 after/post-release map、无 N05 release 结果、无 compute-only／XY。
- 安全清理报告 landed、DISARMED、fixture detached／不存在；项目容器 stop exit 0。fixture 清理时 pitch joint position −0.001 rad、velocity −0.400 rad/s，原始值保留。
- #221 先补回 #218 两个模型，使场景相对基线只多真实顶板，再重跑同一 profile 与门限。详见 [#220 evidence](../evidence/n08-overhead-ceiling-20261024-220.md)。
