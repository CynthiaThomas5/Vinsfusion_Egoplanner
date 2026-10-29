# #118 N06 实际布局动态障碍终端保持

日期：2026-10-23。子项：N06 实际布局 dynamic obstacle／terminal hold planner response。结论：**本 planner-only 子项通过；父 N06 仍为 `in_progress`。** #094 要求的全机支架释放后合法正向准入仍缺。

## 运行顺序与假设

- `n06-20261023-wall-124` 先验证原始 wall 布局中的 +0.4 m X 目标，三张快照和 live body/sweep 通过，但既有墙体使目标 terminal hold raw occupied；goal gate 正确拒绝，未发布曲线、未生成注入障碍。
- 对这三张快照复算后，+0.4 m X、+0.3 m Y 的候选 body、连续 sweep 和 terminal hold 均 raw free；注入点也 raw free。
- `n06-20261023-wall-125` 的基线证书通过。创建 0.3×0.3×0.6 m 盒体后，mapping log 记录 `normalized_cost_exceeded`，MapStatus 关闭并在同 epoch 下更换 map_id；EGO 因 `full_curve_map_id_mismatch` 取消目标并转 `WAIT_TARGET`。没有观察到障碍 raw occupied，也没有取得 emergency hold。该时间关联不能单独证明模型生成是定位门关闭的唯一原因。
- 新假设将唯一主要变量——盒体大小——缩到 0.15 m 立方体；颜色、位置、目标偏移、传感器运动和注入时序保持相同。原始注入点到模型最近角的 map-frame 几何距离为 0.106 m，小于 0.12 m 查询半径；其目标 hold 球与模型相交，当前位置 hold 球保持净空。

## #126 实际证据

运行 `n06-20261023-wall-126` 使用 `wall_box_column`、ROS domain 116、固定镜像 `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`。三张快照均有唯一 source-pose 匹配、source/fusion age ≤0.113/0.047 s，body、20-query continuous sweep、terminal hold 均 raw free。live body/sweep/hold 通过，EGO 发布 40-query、0.416 ms 的完整曲线证书；目标偏移为 `(0.4, 0.3, 0.0) m`。

Gazebo 接受了位于 `(1.4, 0.25, 1.0) m` 世界坐标的 0.15 m 立方体。注入后 epoch、map_id、frame、`input_ready` 和 reset ack 均稳定；source/fusion age 为 0.065/0.099 s。D435i 新融合地图的 `(1.25, 0.1, 0.0) m`、半径 0.12 m 原始查询得到 `occupied`（4 occupied、0 unknown 体素）。同一地图上的当前位置 terminal hold 为 `free`（0 occupied、0 unknown）；目标 terminal hold 为 `occupied`（6 occupied、0 unknown）。

EGO 记录：

1. `Active curve blocked by map (terminal_hold_occupied); checking a stationary emergency hold`
2. `EXEC_TRAJ → EMERGENCY_STOP`
3. emergency hold 的 full-curve 证书 `reason=free`，2 个 query、0.066 ms
4. 发布一条 traj_id 2 的常位置 B 样条；注入后没有非静止曲线，也没有 planner fault。

该 B 样条只被探针观察，未接入 trajectory consumer 或执行器。结果证明：在该 wall 地图、当前配置和一次低速 D435i 诊断运行中，新占据体素能阻断目标 hold，同时保留当前位置的认证静止 hold。

## 产物与哈希

完整机器报告：[JSON](n06-dynamic-obstacle-response-20261023-118.json)。运行原始数据位于 `artifacts/runs/n06-20261023-wall-124/`、`...wall-125/` 与 `...wall-126/`。#126 的关键 SHA-256：

- probe result：`bc82cf7351dd35310e5e1966f789fb61b62f7ce2d82b543ff64c6213cc5952dc`
- run inputs：`3a7addfd550aa5756eb1deb9fb4713e2a42cf4d161933fe6a64186dc0eb67197`
- motion recording：`f10ccc9168a9f25b2900d23c67fa74d5104c41952051e3cca9d22fc01a3144aa`
- mapping log：`6ae58b284f2a994f4632b6d99cacebeea2be379ce18809709e6afabd86cb22c6`
- spawned SDF：`ca4707de83430a06dfb398fb8f1c07598078423d826b34ec9520bf96b144d062`

探针运行时源码 SHA-256 为 `3e3933fa6bf97f635814aad30b4730e4beac1d014101f55450badff0129d93bb`，与 run-input manifest 一致。运行后仅将诊断字段 `late_curve_count_after_emergency_transition` 改为语义准确的 `post_transition_curve_count`；#126 的原始 JSON 保持不变。其 transition 后计数为 1，正是随后发布的静止 emergency hold；验收另检查了注入后所有曲线均静止。

## 边界与下一步

障碍被单次生成后保持静止；没有验证移动障碍、执行器跟踪、机体实际制动、停止距离或实机。#126 清理时 mapping adapter 以 exit -11 结束，发生在 probe 判据通过之后，记录在 mapping log；不把它解释为运行期 planner 失败，也不省略该状态。

#118 增补了 N06 动态地图障碍及 emergency-hold 的实际布局 planner 证据，不是全机合法入口证据。N05 现有 support-release 检查仍 no-go；当前 N06 范围禁止启动其要求的 PX4 DISARMED 状态链，因此 N06 保持 `in_progress`、`next_goal=N06`，不启动 N07。下一子项为 N06.4 范围解除与 full-airframe release 后 fresh admission；动态制动仍属 N08。
