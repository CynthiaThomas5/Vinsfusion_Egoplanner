# N08.2j #220：N08 顶板布局首次支架运行

## 假设、变量与判据

假设是在场景中加入真实 overhead surface 后，深度射线可以将上方运动净空建立为 raw free；顶板本身必须保持 occupied。验收要求 N05 same-run gate 和 EGO 原半径 clearance 通过后才继续 compute-only。

## 结果

静态检查通过：`python3 tools/project_status.py` 报结构 PASS（明确不代表 build/SITL）；新布局 JSON、N05 脚本 shell 语法、Python AST 和原 `n08_overhead_free_sector_view` profile joint limits 均通过；生成的 `n08_overhead_boundary` SDF 被 `gz sdf -k` 判为 `Valid`。模型位于 spawn 上方，pose `[-6.5,0,2.7]`，尺寸 `8×8×0.1 m`，底面 z=2.65 m。

运行 `n08-20261024-220-overhead-ceiling-01` 在支架第 6/15 阶段中止，helper 报 `localization changed or became invalid during physical scan`，末态 localization 为 `normalized_cost_exceeded`、cost 1.029。after/post-release raw map 未生成，因而无法评估 N05 release gate 或顶板下方的 EGO sphere。没有 compute-only、goal、XY 或制动测量。

安全清理报告 vehicle landed、DISARMED、fixture detached 且 Gazebo model list 无 fixture；随后 project stop 成功，容器 exit 0。fixture 记录的 pitch joint 在清理时位置约 −0.001 rad、速度 −0.400 rad/s；该运行没有完成 N05 release 检查，保留此状态细节供审查。

**本次环境并非单变量对照**：N08 顶板布局只包含顶板，漏掉了 #218 `wall_box_column` 的 `n04_box` 与 `n04_column`。目前不能把 VINS 失效或地图结果归因于顶板。完整事实见 [JSON 报告](n08-overhead-ceiling-20261024-220.json) 与运行归档。

## 下一步

#221 保持顶板尺寸、位置、材质、N05 路线和 −0.45 rad 观察姿态不变；在 N08 layout 中补回与 #218 完全相同的 box/column 几何。目标是隔离“额外顶板”这一变量。先跑 N05；只有整条支架扫描及 fresh release gate 都完成，才审计同 run raw map。
