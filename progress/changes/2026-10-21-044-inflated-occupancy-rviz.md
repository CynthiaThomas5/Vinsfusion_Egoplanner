# RViz Inflated Occupancy Map

对应[对话](../../collaboration/dialogues/2026-10-21-044-inflated-occupancy-rviz.md)与[证据](../evidence/ego-inflated-rviz-20261021-01.json)。

修改 `config/rviz/mapping.rviz`、`tools/prepare_mapping_rviz.py`、`config/README.md`：复用现有 EGO `publishMapInflate`，显示实际重映射 `/drone_0_grid/grid_map/occupancy_inflate`。配置为0.1 m方块、Z高度着色，固定坐标系由会话 epoch 生成；drone_id 读取默认规划参数。第三方没有修改或重复导入，因此无需新增依赖补丁。

源码核对：GitHub 固定提交 `23a8d5a191711dd65633df689bd00f55d4dea8f9` 的 `src/planner/plan_env/src/grid_map.cpp` 与本地既有实现均使用 occupancy_buffer_inflate，发布 PointCloud2。场景仓库本身不含地图算法。

运行：初次未加 drone 命名空间未收到膨胀点云，修正后两路都为空；检查确认旧会话 normalized_cost_exceeded（1.0003076745），保护门清空地图。新会话首次重启遗漏 GZ_PARTITION，无传感器，排除；第二次继承原 partition 成功。最终 epoch `5b0d931e56b44d24ac3508a23601b19a`，12秒只读探针收到101帧膨胀点云、100帧原始点云，最大2182／515点，全部有限。截图人工检查有高度着色膨胀方块，RViz 仍有全局 TF warning，未阻止该 frame 下地图显示。全部中间日志保留在 `artifacts/runs/ego-inflated-rviz-20261021-01`。

验证：配置生成与占位符替换断言通过；非法 epoch 拒绝通过；live probe 通过并保存截图。没有修改 ROS 包代码，无新增构建需求。结构检查与 diff 检查通过。未解锁、未使能、未发导航目标；P0–P6/S1–S6不升级。

局限：只证明实时显示，未验证完整房间覆盖、几何精度、净空和飞行。长时定位仍可失效，未放宽阈值。Gazebo 与新 ROS 链及 RViz 继续运行；新进程 PID 在 run 的 vio.pid/rviz.pid，原启动脚本不会单独管理替换后的 ROS 进程，完整关闭请停止该容器。
