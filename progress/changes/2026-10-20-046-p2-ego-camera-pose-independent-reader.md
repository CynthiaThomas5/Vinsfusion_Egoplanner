# P2 EGO camera-pose independent-reader trace #290

对应对话摘要：[2026-10-20-046](../../collaboration/dialogues/2026-10-20-046-p2-ego-camera-pose-independent-reader.md)。轻量证据：[p2-ego-camera-pose-independent-reader-20261020-290.json](../evidence/p2-ego-camera-pose-independent-reader-20261020-290.json)。完整原始哈希清单在 `artifacts/runs/p2-ego-camera-pose-observer-20261020-290/run-report.json`。

## 结果

- #290 在 #289 的 run-local unknown-as-obstacle EGO 构建、force-driven D435i fixture 与 planner-only 组合上，加入一个可靠 QoS、depth=50 的独立 `/drone_0_camera_pose` reader。它仅接收轻量 `PoseStamped`，记录主机 realtime/monotonic 与源时间戳；未额外订阅深度图。
- 观察者收到 1,264 条位姿和70条心跳，frame 固定为当前 epoch。源 stamp 严格递增；全轮最大主机收包间隔0.2172秒、最大源时间间隔66 ms。
- EGO 出现32条 `odom or depth lost`，分成两簇：仿真时刻37.132–37.802秒期间同步计数固定956；43.539–43.997秒期间固定1121。两簇内独立 observer 均持续收到位姿；加前后1秒窗口后分别有61/57条 observer 样本，最大源时间间隔均66 ms；EGO `last_sync_in_map=true`。
- 两簇均早于 mapping adapter 因 `normalized_cost_exceeded` 关闭 map gate（run wall elapsed约62.92秒）。因此后续定位失效/地图清理不能解释这两簇；publisher-wide camera-pose outage 也不足以解释。但独立 reader 的收包不能证明同一 DDS 样本已到达 EGO 自己的 DataReader，也未观察 EGO depth reader，不能区分 pose-reader、depth-reader 与 `message_filters` 配对问题。
- 探针发出目标并捕获98条 planner spline；地图派发时为902个 occupied、15,360个 inflated 点。无轨迹执行器、PX4/control 节点或控制话题；无真值话题订阅。该数值不是避障或净空结果。
- 85.70秒 host realtime/monotonic监测含8,501个样本，偏移全距20.6 μs，最大相邻变化20.3 μs，未见明显回拨。
- 事后核对实际运行脚本发现 #290 复用了 #289 的 `ROS_DOMAIN_ID=136` 与 Gazebo partition。两轮非并发，启动前未发现项目容器/节点，但没有跨domain隔离；报告和证据元数据已更正，不能排除domain环境混杂。

## 修改与验证

- 新增 run-local `pose_observer.py`、`analyze_pose_delivery.py` 与 #290 启动脚本；未修改自维护源码、固定 vendor 源码、canonical patch 顺序、`dependencies/sources.json` 或健康阈值。
- Jazzy 镜像内 rclpy QoS import 与 Python 语法检查通过；隔离 planner-only run 正常完成并生成 observer stream、EGO log、同步对齐分析、地图/定位状态、控制隔离清单和时钟监测。
- observer 在 SIGINT 时写出终止 marker 和完整样本后，rclpy 因外部 context shutdown 打印清理异常。接收数据完整，但此清理路径仍需修正后复用；异常不解释任何 EGO timeout。
- 原始运行文件的 SHA-256 与大小列在 run report 中；报告与轻量证据均引用其哈希。

## 状态与下一步

此诊断只把相机位姿话题到达边界向前缩小了一步。下一步在隔离 EGO 源码副本应用既有 `0012→0013→0015` 输入回调计数诊断，并与低带宽独立位姿观察对齐，区分 EGO filter 回调缺口与同步器配对缺口；不改变 canonical vendor 源码或健康门。GOAL C 仍 pending，unknown patch仍为实验候选，GOAL A–H未完成。
