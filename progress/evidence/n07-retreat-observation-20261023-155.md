# #155 N07 远后视角诊断

## 结果

- 运行：`n07-20261023-155-01`，固定镜像、`spawn=-6.5,0,0.3,0,0,0`，`n06_full_airframe_retreat_240_translation_only`。
- 6/6 阶段完成；路径后退 2.4m 并返回；10,177 条 fixture trace 全部为 valid/Tracking，单一 epoch，normalized cost 范围 0.073–0.604。fixture 最终确认 detached，删除服务确认成功且 Gazebo 场景中无 fixture；PX4 状态仅 DISARMED。
- 初始 fresh gate 拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`。完整观测后、fixture 尚连接时的五阶段 N05 online/offline 一致接受，所有阶段 maximum unknown=0、maximum occupied=0。
- fixture helper 在 detach 后的短暂状态检查以 `localization changed or became invalid during physical scan` 返回码 2，尽管 route trace 全 valid、最后缓存 LocalizationStatus valid 且支架移除已确认。现有 wrapper 因此停止容器，**没有采集释放后的 fresh N05 gate**。attached gate 不等于可起飞准入，本轮没有解锁或飞行。

## 解释与下一步

这支持“更远同轴后退可补齐当前 N05 地图未知区”的假设：HOLD unknown 从此前 422 降至 attached gate 的 0。仍缺少的唯一 N05 证据是 fixture 释放后的新鲜五阶段检查；后续冷启动将手动控制 detach 与等待，重新读取定位／地图新鲜状态并执行 online/offline gate。只有该 released gate 通过后，才开始 N07 第一次无目标悬停。

机器报告：[n07-retreat-observation-20261023-155.json](n07-retreat-observation-20261023-155.json)。逐文件哈希、原始阶段记录、轨迹和门禁报告均在 [`artifacts/runs/n07-20261023-155-01/`](../../artifacts/runs/n07-20261023-155-01/)。
