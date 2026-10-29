#268：unknown 转向保持区的前向 EGO 定位段

## 依据与假设

#267 的前向 0.6 m 制动段通过，但原地 yaw 前 raw turn-hold 球有 30 格 unknown。起飞前同身份地图将这些格分类为 free；飞行后它们成为机头后方 unknown。用 #267 的 fresh pre-turn raw map 离线复算，额外前移 0.22 m 的 9 个 capsule 查询和候选转向球均为 raw-free；0.22 m 略高于 EGO 局部路径 0.2 m 下限。归档图上的返航 capsule 在转头前仍有 unknown，因此要求先转头、更新地图，再认证返航。

唯一主要变量：仅在初始 turn-hold query 的 reason 为 `unknown` 时，先执行一次 0.22 m、保持当前 yaw 的前向 EGO 目标；其他失败原因不触发额外移动。

## 实现

- N08 trial profile 增加 `turn_approach_distance_m=0.22`，校验只接受 0 或 0.20–0.25 m 的有界值。
- `certify_trial_turn_approach` 在 fresh raw map 上同时检查当前到候选点的 tracking-margin capsule 与候选点完整转向球；任一 unknown、occupied、越界或查询异常都 fail-closed。
- mission runner 只有通过该门后才发单个 EGO 前向 goal；要求在线 spline 速度、机头前向、连续位置管道证书和实际端点都通过。随后重新取图、核查实际 turn-hold 球，再走 stationary yaw、转向后 fresh map、机头前向 EGO return。
- 原 0.6 m 制动 goal 与 `post_goal_hold_end_sim_ns` 保持原值，独立制动评估仍只分析该段。定位段把整段路线 longitudinal tube 扩至 0.82 m；横／垂 5 cm 管道、0.25 m tracking margin、0.12 m/s vector cap、unknown 判据和每个 raw-map 准入门均不改变。返航最大距离只相应增加定位段长度，仍受 raw corridor capsule 与连续样条证书约束。

## 当前验证与剩余项

- `PYTHONPATH=tools python3 -m unittest tools.test_n08_trial_gate`：9/9 通过，覆盖 5 cm 原门限、unknown rear strip 的候选前移、位置段/转向球未知拒绝和 EGO 最短段边界。
- `python3 -m py_compile ...` 因现存 root-owned `tools/__pycache__` 无写权限而未能落盘；对三个脚本执行 Python 内存 `compile(source, filename, 'exec')`，均通过。
- `git diff --check` 通过；`python3 tools/project_status.py` 结构检查通过（它明确不代表 ROS build 或 SITL）。
- 仅修改 N08 runner、门控 helper、对应测试与 trial config；未改 ROS package、EGO C++、N05 admission、速度配置或控制桥，因此不要求 colcon build。
- #268 fresh N05/SITL 已运行，结果为 fail-safe 拒绝：N05 扫描15/15、post-release及mission current-area准入与40.005秒preflight通过；首条0.6m EGO曲线最大横／垂偏差5.265cm，超出5cm管道2.647mm。因拒绝发生在#268新增定位段之前，0.22m定位、原地180°转头和转头后机头前向EGO返航均未执行。没有新增制动数据；末态DISARMED/landed并已停止容器。完整证据见[#268报告](../evidence/n08-forward-positioning-return-refusal-20261025-268.md)。
- 保留5cm门限，下一子项#269只在发首个目标前增加`|PX4 vz|<0.01m/s`稳定1秒的诊断前置条件，同时保留原总速度`<0.03m/s`稳定1秒。新门控测试12/12、Python内存编译通过；需用新冷启动确认该条件在20秒等待窗内可达到。若不能达到，发目标前安全停止并记录，继续诊断；条件达到后仍须由原5cm曲线证书作独立判定。
