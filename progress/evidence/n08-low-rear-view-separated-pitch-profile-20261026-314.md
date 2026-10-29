# N08 #314：低位后向观察分段转向 profile

状态：profile 静态配置通过；SITL 已执行并在第14/19阶段因定位健康门拒绝，见[运行报告](n08-low-rear-separated-yaw-lockout-20261026-314.md)。

## 试验变量

基于 #313 的定位代价锁存，#314 保留其前13阶段、低位后向观察位置、−0.35 rad俯仰目标和所有门限。后向阶段先用8 s同时将yaw从0转到−π/2并将pitch从0调整到−0.35 rad；再以固定pitch继续偏航至−π 18 s并保持4 s；保持pitch回转至yaw=−π/2、再到0；最后用8 s复位pitch。profile 共19阶段、478仿真秒，最终关节回到初始位置。

原假设意图把俯仰和偏航分开，但静态核对发现第一个后向阶段仍同时改变yaw与pitch。实际测试变量是将180°后向转向拆为两个90°阶段，第一段同时加入俯仰、第二段固定俯仰继续偏航；该profile未实现轴向隔离。#315改为yaw全程pitch=0，并仅在后向静止点俯仰观察。

## 静态验证

- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_preflight_scan`：45/45 passed。
- `python3 tools/project_status.py`：Structure/design PASS。
- JSON 解析、N05 wrapper shell 语法和 `git diff --check` 均通过。
- `validate_profile` 确认19阶段所有 x/z/yaw/pitch 目标均在夹具关节限位内，最终目标回到 `[0,0,0,0]`；profile runner 和 host wrapper 均允许此 profile。

## 下一步

冷启动 `n08-cancel-highspeed-prescan-20261026-314`。要求全部扫描阶段、fixture detach/model absence/landed、同身份 post-release/current-area N05 online/offline、40 s read-only preflight 和 N08 前向几何门通过后，才继续 motion-cancel 单目标。拒绝即不发 goal/enable，独立读回并停止本次容器。

机器摘要：[JSON](n08-low-rear-view-separated-pitch-profile-20261026-314.json)。
