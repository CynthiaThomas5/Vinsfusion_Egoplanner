# N08 #307：后向短保持扫描在回中后下降时被定位健康门拒绝

状态：未通过，未进入释放后 N05 或 N08 mission。

- 新冷启动使用 `n08_overhead_free_sector_negative_y_rear_short_hold`，17阶段配置；完成14阶段。负Y后向观察、yaw 回到 0 均完成，失败转移到第14阶段的支架下降。支架 z 从1.0 m降至约0.899 m时最后一条 trace 仍有效、cost=0.96961；fixture 最终锁存 `normalized_cost_exceeded`、cost=1.0098607。阈值未改。
- 初始 N05 因 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope` 拒绝；扫描未进入 prescan-ready 窗口，释放后 N05、N08 起点／前向路径／终点检查均未执行。没有 goal、enable、控制发布或飞行。
- 失败清理把支架回到初始位置并 detach，Gazebo 确认 fixture 模型不存在；PX4 LandDetector 确认 landed。独立只读 topic 读回 bridge `DISABLED`、control disabled、disarmed、landed；PX4 `arming_state=1`、`landed=true`、`ground_contact=true`、`at_rest=true`。独立 N05 snapshot helper 另因缺少 optimized odometry 超时，失败记录保留；此读回没有被当作 N05 准入。
- `bash tools/project.sh stop n08-cancel-highspeed-prescan-20261026-307` 返回0；容器最终 `exited 0`。其他容器未触碰。

## 判别与后续

#306 在回中时越过cost门；#307 缩短后向静止保持后，回中完成，但代价在下降阶段升高。#248 已显示同类负Y视角后的慢下降在相近高度仍越门，因此不再以“只把下降放慢”作为下一假设。

此外，#305 同身份 raw map 的 N05 entry通过，但 N08 单目标准入的球形起点保持／前向路径仍把主要位于机尾侧的 unknown 纳入查询。N05 已使用实际 X500/D435i 碰撞几何加既有空间误差预算；N08 目前用 `obstacles_inflation_m` 的外接球再加0.25 m tracking margin。下一项 #308 将先用 #305 存档地图审计实际碰撞几何与相同误差／tracking预算的形状查询，确认是否能在不减小任何距离预算的情况下排除外接球带来的过度拒绝；只做离线几何对照，不代表飞行通过。若能通过原阈值，再改实现、加拒绝回归并以新冷启动验证；否则保持拒绝并转向新的可行动证据。

原始运行在 `artifacts/runs/n08-cancel-highspeed-prescan-20261026-307/`。机器摘要与 SHA256 在同目录数据的本页 JSON 摘要中。
