# #207：地面 SITL 读取 PX4 时间参考

对话摘要：[N07 PX4 时间参考地面读回](../../collaboration/dialogues/2026-10-24-207-n07-px4-clock-ground-readback.md)。报告：[在线读回](../evidence/n07-px4-clock-live-ground-20261024-207.md)、[机器数据](../evidence/n07-px4-clock-live-ground-20261024-207.json)。

## 验证

- 以 `bash tools/project.sh sim n07-20261024-207-clock-ground` 启动地面 SITL；未武装、未起飞、bridge 控制保持 `DISABLED`。
- 通过只读 ROS 订阅读取 `/uav_px4_bridge/status/detail`：HRT `31420000 us`、PX4 时间域有效、HRT 与映射 `/clock` gap 为 0、clock 回调龄约 3 ms；PX4 遥测源龄均在原限值内。
- 使用 `bash tools/project.sh stop n07-20261024-207-clock-ground` 收尾，返回 0；容器 exit 0，项目容器已停止。

此地面检查验证实时桥接接线；#203 的 196 ms 延迟事件仍由历史轨迹复算验证。没有重跑 #198/#200/#204，也未计入 hover 次数。

## 状态

结合 #198/#200/#204 的累计 3/3、未改变门限的 build/offline replay 和 #207 live ground readback，N07 限定出口通过。后续主线为 N08；本轮未执行 N08。
