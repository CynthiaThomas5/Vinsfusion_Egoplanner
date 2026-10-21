# P2 深度健康门

- 用户要求继续推进 P0–P6；在两次 source-stamp 深度断流注入后，实现了真实 ROS 深度新鲜度状态节点。
- `uav_mapping/depth_health_monitor` 校验 `depth_optical_frame`、`32FC1`、分辨率、行步长、数据长度和时间戳单调性；超时发布 `STALE`，恢复新帧后发布 `READY`。时间戳回退锁定到节点重启。
- `DepthHealth` 接口可靠 transient-local 发布 `/mapping/depth_health`。当前阈值为 1.0 秒稳态墙钟，标记 PROVISIONAL；不检验像素 NaN/Inf、深度精度、定位状态或地图结果。
- Jazzy 新 build/install 下 `uav_interfaces` 与 `uav_mapping` 构建通过；纯逻辑 4 项测试通过。两个独立 ROS domain 回放同一深度 bag，目标断流时均 `READY → STALE`，恢复后均回到 `READY`。
- 探索记录：0.5 秒探索阈值在有丢帧回放里产生额外 stale/ready 切换，之后调整到1.0秒并重跑。第一次 monitor 用 SIGTERM 停止时出现 `ExternalShutdownException`，现已正常捕获。中间探索报告复用了最终 run 文件名并被覆盖；最终验收报告只引用后续独立目录中的两次干净结果。
- 证据：`progress/evidence/p2-depth-health-gate.json`。不代表地图实现或 P2/E 完成；还需要地图节点使用该状态关闭地图并清理旧会话数据，再验证规划和 PX4 响应。
