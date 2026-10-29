# #158 N07 1.8m 后退观测结果

run `n07-20261023-158-01` 在 `spawn=(-6.5, 0, 0.3)` 完成 DISARMED 全机支架扫描。目标 profile 为 `n07_spawn_minus65_retreat_180_translation_only`，六阶段全部完成；10122 条轨迹记录均为有效 VINS 状态，单一 epoch `dbc75d42412e4999911a1d4a6649edae`，normalized cost 峰值 0.66134。

## 定位与支架收尾

VINS accel bias 峰值为 0.148524m/s²，N02 health 锁存门限为 0.15m/s²，余量仅 0.001476m/s²。该路线没有锁存，但不适合再增加同轴后退距离。扫描结束后 fixture remove service 得到确认、Gazebo model list 中没有扫描支架、`fixture_may_remain_attached=false`；最后定位 valid，PX4 arming state 为 1（DISARMED）。fixture helper 在六阶段完成和 detach 后仍报告 `localization changed or became invalid during physical scan`；此报错保留为工具结果，机械移除证据和 released gate 单独记录。容器经项目 stop 流程退出 0。

## N05 准入

初始、attached 和 released 检查均拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`。attached/released 身份保持同一 epoch/map；online gate 与嵌入式离线 sweep 决策、阶段计数一致。released 的 HOLD 留 3 个 unknown，中心为：

- `(-0.55, 0.35, 1.15)m`
- `(-0.45, 0.35, 1.15)m`
- `(-0.35, 0.35, 1.15)m`

raw-ground plane 为 `z=-0.35m`，这 3 个未知格均在地面以上；地下未知数为 0。起飞／降落接触相位各有 122 个 unknown，ASCENT／DESCENT 各有 110 个。ground boundary 下排除数为 44／32／0／32／44；未知体素仍按既定 N05 规则拒绝。

宿主机独立回放一开始因 exact float-dict equality 将 ground-plane 拟合系数约 `1e-16` 的舍入差判为 mismatch；拒绝原因和所有阶段计数相同。修复 `evaluate_n05_entry.py` 为浮点末位使用 `1e-12` 数值容差后，attached/released 两份独立回放都匹配。布尔状态、字符串、整数体素计数仍严格比较，N05 门禁本身未改。`python3 tools/test_n05_entry.py`：11 passed。

## 结果与产物

- released N05：未通过；没有启动或授权解锁。
- N07 合格悬停：`0/3`。
- 静态全机路线最小连续非地面净空下界：0.889410m（地面和支架未纳入，不是飞行／制动证书）。
- 机器可读摘要：[n07-retreat-observation-20261023-158.json](n07-retreat-observation-20261023-158.json)
- attached / released unknown 逐格审计：[attached](n07-hold-unknown-volume-attached-retreat-180-20261023-158.json)、[released](n07-hold-unknown-volume-release-retreat-180-20261023-158.json)
- 独立离线回放：[attached](n07-n05-attached-offline-replay-20261023-158.json)、[released](n07-n05-release-offline-replay-20261023-158-host.json)
- 路线静态检查：[JSON](n07-retreat-180-route-geometry-20261023-158.json)、[说明](n07-retreat-180-route-geometry-20261023-158.md)
- 原始运行数据：`artifacts/runs/n07-20261023-158-01/`；关键 SHA-256 见 JSON。

下一项 #159 保持 1.8m 平移和 pitch=0，只在远端增加 +0.15rad yaw 视角，目标是从另一水平角度观察 y=+0.35m 的少量未知格。仍以 released fresh N05 五阶段通过为解锁前置条件。
