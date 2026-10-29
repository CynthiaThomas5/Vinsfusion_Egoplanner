# N09 接触观测与 live refusal

## 范围

用户要求按已确认的规划完成 N09。继续保持 Goal 模式，目标出口仍是三次独立冷启动的单程三维/yaw 目标、独立真值到达、任务全程 fresh localization/map、可拒绝未知/不可达目标、正确 cancel/replace/timeout 和无违规接触。N08/N07 不重测。

## 决定

- “简单航点”走已有 `NavigateToPose` action，经同一 current epoch/map 查询后由 EGO 规划，再由唯一 `uav_px4_bridge` 控制 PX4；不重启旧 `/move_base_simple/goal` 固定高度直通。
- 独立的 Gazebo Contact sensors 是“无违规接触”验收的直接证据。仅在每个 N09 run 的 overlay 模型上添加传感器，不修改碰撞几何/物理/控制；六个 topic 在起飞前未全部发布就不飞。允许起飞前地面接触及 LANDING/LANDED 地面接触；其他接触算失败，并要求观察到着陆 contact 证明采集有效。
- 每次真实 mission 前发送一个地图外目标，要求当前 live action 明确拒绝，未进入 EGO、桥不解锁、不改变当前 epoch/map。合成 adapter 拒绝回归同时保留。
- 首次接触 overlay 启动因 cwd 相对路径在 Gazebo 前退出；第二次确认六个 contact 话题真实存在，但由于后续修改 runner 指纹，未运行 mission，保持 DISABLED/未解锁/landed 并安全停止。两个启动尝试都不计 flight/pilot/重复次数。

## 当前状态

N09.1 action/lifecycle 回归与 ROS 构建已通过。N09.2 仍待新的完整 PX4 SITL pilot。当前 profile 是 forward 0.4 m、up 0.1 m、yaw +0.2 rad，native tolerance 0.05 m / 0.1 rad；这还只是候选，pilot 通过前不冻结为正式重复。若实时 N05/N06、PX4 preflight 或 EGO map certificate 拒绝，保存 no-go 并据因果证据处理，不修改 unknown 或速度门限绕过。
