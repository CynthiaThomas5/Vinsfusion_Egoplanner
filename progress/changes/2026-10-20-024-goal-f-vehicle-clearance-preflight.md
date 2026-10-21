# GOAL F：机体 clearance 几何前置审计与 EGO 膨胀配置

对话摘要：[2026-10-20-024](../../collaboration/dialogues/2026-10-20-024-goal-f-vehicle-clearance-preflight.md)

## 改动

- 新增 [GOAL F 前置证据](../evidence/p0-ego-obstacle-inflation-20261020-245.json) 与原始几何计算结果：按 EGO 的 `d435i_imu` 参考原点计算，x500 的9个 SDF 碰撞盒方向不变球半径为 `0.470884 m`；相机 SDF 无碰撞体，旋翼碰撞未建模扫掠体积。
- EGO plan_env 的栅格分辨率为 `0.1 m`，既有 inflation 为 `0.099 m`，对应一个体素索引步。新字段 `obstacles_inflation_m` 加入默认与低动态配置；VIO/EGO bringup 和 debug_truth launch 均从选定 planner JSON 传入 `grid_map/obstacles_inflation`。原值保持不变，仍是 PROVISIONAL。
- 第三方 launch 参数化保存为 [EGO patch 0019](../../dependencies/patches/ego/0019-configurable-obstacle-inflation.patch)，基准为 pinned EGO `23a8d5a191711dd65633df689bd00f55d4dea8f9` 的 canonical patch 0018 之后；补丁可从修改前文件重放至逐字节一致。
- 更新依赖清单、EGO 补丁记录、F 检查表、P0/P4 里程碑证据引用、配置说明与当前进度。检查表 F 仍为 pending；P0–P3/P4–P6 阶段状态未改。

## 验证

- `python3 tools/test_vio_ego_bringup_config.py`：7/7通过，覆盖配置映射、替代 planner profile 和负 inflation 拒绝。
- 固定 Jazzy 镜像新目录 `colcon --packages-up-to ego_planner uav_px4_bridge`：14包通过；新增 debug_truth 参数转交后 `uav_px4_bridge` 增量构建1/1通过。
- 已安装 `advanced_param.launch.py --show-args` 显示 `obstacles_inflation`；隔离 EGO-only 节点 `ros2 param get /drone_0_ego_planner_node grid_map/obstacles_inflation` 返回 `0.099`。节点保持 INIT，未启动 PX4、控制桥、轨迹服务器、传感器或真值源。
- `python3 tools/project_status.py` 结构检查通过；JSON 解析、Python 语法、`git diff --check` 与 `git diff --cached --check` 通过。

## 局限与下一步

静态几何审计不证明机体实际净空；模型缺少相机壳体与旋翼扫掠体积。`0.099 m` 仅为保留既有行为，不是 clearance 标准。GOAL F 仍需多障碍 profile、同运行地图／定位／跟踪误差、最小机体间距、最大数据年龄、重规划期限、故障检测／退出超时与实测制动基线；正式 D/E 验收尚未开始，不冻结 `config/acceptance.json`。
