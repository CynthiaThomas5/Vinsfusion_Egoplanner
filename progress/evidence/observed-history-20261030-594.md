# #594 RViz累计观测地图

限定功能 **PASS**；机器可读结果、原始输入哈希见[JSON](observed-history-20261030-594.json)。不是全局SLAM、当前可通行地图或新的正式场景资格。

## 实现与边界

新增 `uav_mapping/voxel_history.py`、`observed_history.py`。默认可视化启动创建 `observed_obstacle_history`；读取 `/grid_map/occupancy`、定位/地图状态及仿真时钟，仅发布 `/visualization/mapping/observed_history`（另有标准rosout/parameter_events）。实际运行节点图见 `artifacts/runs/gui-20261030-115354-3418835/history-node-graph.txt`，无控制/规划/真值输入输出。

按所选planner的体素分辨率/边界去重，历史占据只做并集；默认1Hz、25万体素上限，满时保留旧体素并告警省略新体素。map_id变化立即清空，重置确认前不接收云，确认时间戳作为新云下限；旧身份消息拒绝。epoch变化清空并锁住旧可视化会话，时间倒退清空并等待新地图身份。Reliable/Transient Local提供完整缓存给晚订阅者。RViz新增青色 `Observed Obstacle History (display only)`，局部 `Inflated Occupancy Map`保持。

## 验证

| 类型 | 命令 | 结果 |
|---|---|---|
| 构建 | `bash tools/project.sh build ros` | 18ROS包PASS |
| 单元/ROS | `bash tools/project.sh test` | 740单元测试、原有2套ROS及新增history ROS probe全部PASS |
| 新ROS接口 | `probe_observed_history.py --project-root /workspace` | 分离区域保留、晚订阅完整缓存、旧frame拒绝、map重置/ack/时间屏障、旧map_id、时间倒退、epoch清空与显示专用发布者PASS |
| GUI/SITL | `./start.sh`、`bash tools/project.sh mission gui-20261030-115354-3418835` | 默认16m任务qualification全部7项PASS，正常落地上锁 |
| 只读保留实测 | `record_observed_history.py /workspace/artifacts/runs/gui-20261030-115354-3418835` | 见下表 |
| 结构/格式 | `python3 tools/project_status.py`、`git diff --check` | PASS；不作为飞行证据 |

实际同会话数据：

| 指标 | 体素数 |
|---|---:|
| 起点初始局部云 | 588 |
| 终点局部云 | 844 |
| 最终累计云 | 5850 |
| 起点体素在最终局部云中 | 0 |
| 起点体素在最终累计云中 | **588/588** |
| 累计云中不属于最终局部云的体素 | 5006 |

记录器接收1686帧local和187帧history；对应原始结果为run内 `observed-history-retention.json`。`qualification.json`独立到达、接触、正常终态、核心身份、唯一控制均通过。原始日志在 `artifacts/runs/observed-history-20261030-594-checks/`。

此前两次准备会话未飞行：115057启动后为加强reset确认边界停止；115224因启动后修改包README导致运行指纹变化，任务入口明确拒绝，正常关闭。最终115354是本候选唯一实际飞行，未反复重试物理参数或改变门限。

## 局限与收尾

这是raw占据点历史，不会因后续free观测删除旧点；定位漂移可能留下重影。只覆盖实际发布的点、地图边界及原有高度裁剪，不补未知或完整世界地图。内存缓存不自动保存/跨进程恢复。原规划地图、膨胀参数、唯一桥接器、控制与导航算法保持原行为。

停止原因：本次有界功能和验证完成。GUI `gui-20261030-115354-3418835`按用户查看需求保留，已正常落地上锁/控制关闭；查看后可执行 `./start.sh stop`。无自动下一任务，无源码提交/推送。
