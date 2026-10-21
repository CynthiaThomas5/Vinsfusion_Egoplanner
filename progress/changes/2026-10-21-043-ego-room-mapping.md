# 新房间静态局部建图预览

对应[对话](../../collaboration/dialogues/2026-10-21-043-ego-room-mapping.md)，[证据](../evidence/ego-room-mapping-20261021-01.json)。

- 文件：新增本记录、对话摘要、轻量证据，更新 CURRENT；运行脚本、配置、构建、截图、点云及日志保存在 `artifacts/runs/ego-room-mapping-20261021-01`。没有修改算法、健康阈值或控制源码；阶段不升级。
- 启动：固定 GPU 镜像下构建当前6个自维护包（17.2秒通过），按当前生成器加载新房间和 x500_d435i。先等待原始 IMU 静止，再启动 `vio_closed_loop_ego_px4.launch.py`，Gazebo 与 RViz 均已打开。容器 `d435i-ego-room-mapping-20261021-01` 保持运行。
- 观察：`observe-mapping.py` 记录70.03墙钟秒，有61次 ready 状态采样；VINS 首次有效后采样中无 invalid，最多537个占据点，最后转发深度计数257。仅短时静止局部建图，不是全房或长时验收。
- 快照：`tools/probe_map_snapshot.py --seconds 8 --require-pair` 成功，得到同 epoch/map_id/frame/时间戳的526点快照；JSON文件 `occupied-cloud.json` 独立回读，点数和宽高相符，XYZ全部有限。
- 控制：未调用使能服务、未发目标。独立 CLI 读到 DISABLED、未解锁、landed、control_enabled=false，同时 reason=external_odometry_stale、ready=false，不代表能飞。主观察器 bridge 订阅最初 QoS 不匹配，字段为空，已修正运行脚本供后续使用；控制状态依据独立 CLI。短发现窗口 topic list 不完整，不用于证明全图隔离；node info 仅证明桥接订阅无真值，不能替代完整图审计。
- 验证：6包构建通过；运行脚本 bash 语法／Python 编译检查、`python3 tools/project_status.py` 与 `git diff --check` 完成前执行。结构通过只代表仓库一致。
- 局限与下一步：当前相机视野中的稀疏局部地图可见；未验证移动增量、全房覆盖、独立几何精度、规划执行和飞行。运行期间 GUI 有明显负载，不能将70墙钟秒当作70仿真秒。保持窗口，按用户下一步指示推进。
