# 2026-10-26 #314：拆分低位 rear scan 姿态运动

- 目标：判别 #313 的定位 cost lockout 是否由低位 yaw 与 pitch 同时变化引起。
- 修改：新建 `n08_overhead_free_sector_negative_y_rear_short_hold_low_rear_view_separated_pitch`。保留 #313 前13阶段；后向180°转向拆成两个90°阶段，第一阶段仍同时改变yaw和pitch，第二阶段固定pitch继续偏航；返程阶段固定pitch，最后单独复位pitch。profile 19阶段、总时长478仿真秒。注册到 fixture runner、宿主 wrapper，并新增阶段与末姿态回归。之后发现早先“轴向分离”的说明不符合目标序列，已在 #314 SITL evidence 中更正。
- 阈值：健康、速度、地图、空间与 tracking 阈值均未改变；普通 flight 仍单程前向。
- 静态验证：45项 profile tests，project_status Structure/design，JSON、shell语法、joint-limit和diff check均通过。
- 验收：#314 SITL 在第14/19阶段因定位健康门拒绝；未达到释放后 N05／preflight／前向几何门，未发目标或启用控制。
- 证据：[profile 报告](../evidence/n08-low-rear-view-separated-pitch-profile-20261026-314.md)、[机器摘要](../evidence/n08-low-rear-view-separated-pitch-profile-20261026-314.json)、[对话摘要](../../collaboration/dialogues/2026-10-26-314-n08-low-rear-view-separated-pitch-profile.md)。
