# N05 起降入口与自身过滤

日期：2026-10-23

## 任务摘要

用户通过 `codex resume --last` 恢复 Goal 完成模式，指定继续完成 N05。范围包含起飞点、上升、保持、下降／着陆区的可执行规则与在线检查；至少两个布局的离线扫掠与未武装准入对照；未知或信息不足拒绝；几何、坐标、唯一包络配置和地图快照证据。

## 已确认基础

- N01 与 N04 已通过各自限定出口，N05 依赖已满足。
- x500+D435i 固定模型和 `tools/audit_vehicle_envelope.py` 是当前唯一几何来源；参考点为 `d435i_link` 原点／相机 IMU。
- N04 提供两种布局的当前源码地图快照和 raw 分类数据；#065 仅有远离起点的一个 0.5 m free 球，不构成起飞准入。
- plan_env 球查询没有地面接触掩码。N05 规则不借此清除任何障碍或未知区域。
- 首轮 `wall_box_column` 运行中，扫描前 live checker 暴露 PX4 bridge status QoS 不匹配；请求改为 reliable/volatile 后通过。

## 决定和实现

- 建立唯一 `config/components/navigation/vehicle_envelope.json`，将 SDF 包络、N01/N04 已测误差、体素量化和扫掠采样误差线性相加。该预算为保守的诊断初值，不是硬误差界或飞行门限。
- 在线检查从当前 raw occupancy snapshot 读取体素；不使用真值／完整场景清空数据。地面接触只考虑 x500 SDF 中两条 skid crossbar，且要求 landed 状态和 raw-map 地面平面。
- `TAKEOFF_CONTACT`、`ASCENT`、`HOLD`、`DESCENT`、`LANDING_CONTACT` 使用同一误差扩张包络；拒绝越界、unknown、occupied、姿态异常和过期／错误身份数据，不设起点豁免。
- 支架扫描只作为观察证据；向无支架起飞迁移要求同身份新鲜地图、位姿连续及释放后再次准入。现有 base_link gantry 本身不证明可安全无支架转移。
- plan_env `ground_height_m` 已从 `-0.15` 调至 `-0.65`，覆盖相机 IMU 原点以下的全机下缘区域；此项仍需由新鲜 SITL 栅格快照验证。
- `wall-r02` 后检在当前 VIO z 约 −0.0213 m 时将 plane search 高度上限设为 center−0.1 m，恰好排除了中心 z=−0.10 m、但与物理界面相交的 0.10 m 栅格。该归档快照有 128 个候选 raw occupied voxel、1.0×1.6 m XY 跨度、约 1e−16 m p95 plane residual。策略现允许按 half-resolution 纳入相交体素中心，并保留 occupied-only、跨度、残差和坡度门限。
- `wall-r02` 完整 DISARMED 支架扫描后夹具状态由 attached 变为 detached，fixture removed 确认；在线系统从未切换到 Offboard 或发布导航目标。扫描前 full-airframe raw unknown 拒绝被保留。
- 当前算法版本 wall r03 也完成 12 个 coverage 阶段。前后准入均因完整机体包络 raw unknown 被拒绝；独立 archive replay 与在线结果一致，epoch/map_id 在扫描期间未变。runner 没有获得 Gazebo fixture remove 服务正响应，但 detached 状态及模型列表确认 fixture 已不存在，bridge 同时为 DISABLED／disarmed／landed；核对后才停止容器。诊断 pass 只表示证据身份、回放与安全清理一致，不表示准入通过。
- 当前 corridor r01 也完成 12 阶段，前／后 attached 快照同身份并因 raw unknown 拒绝，在线／离线相同。fixture remove ack 和模型缺失均获确认；释放后 scanner 的短时 health check 不满足，故不把 attached 准入结果外推为释放后状态。
- 因 `prescan_transfer` 明确要求支持释放后重新执行在线准入，runner 已增加 `n05-post-release` live snapshot/replay；若释放后 prerequisites 不可用，检查器保存结构化 fail-closed error，汇总报告 transfer gate 为 false。当前版本需重新跑两个布局以获取释放后的检查结果。
- wall r04 完成更新后的流程，attached 后 raw unknown 拒绝，released 后 120 秒仍未收到完整当前状态；同一时期 VIO 输入 adapter 记录 `telemetry_stale`，扫描器记录 fresh PX4 DISARMED status receipt 超时。相关日志 SHA 已在 run artifact 关联报告中记录。该 transfer 失败未被后续假定恢复。

## 进展

- N05.1 几何与预算配置已完成，源哈希通过审计。
- N05.2 规则实现、在线只读检查和归档复算已完成；当前 8 项入口规则测试、6 项支架流程测试通过。
- N05.3 的 `wall-r01` 在创建夹具前因 QoS 失败停止；`wall-r02` 运行完整 199 s 扫描并安全拆夹具，但后检触发 ground voxel 边界和 evaluator early-refusal 字段缺失问题。两项均已修正；r02 留作诊断，不与当前代码版本混作最终证据。
- wall r03／corridor r01 附着状态下的入口检查均拒绝 unknown。wall r04 按新 runner 再次验证了 released check 失效，原因为完整状态集缺失并伴随 `telemetry_stale` 记录。当前正在补足状态缺失诊断，并用 corridor r02 判断其是否跨布局复现；transfer gate 继续关闭。

## 待完成

1. 执行更新后的 `corridor_box_column` r02，保存 released 后 live snapshot/replay 或带缺失状态列表的结构化拒绝。
2. 跨布局比较 before、attached-after 和 released-after 准入、map identity、full-airframe sweep 分类、未知拒绝与 pose shift；确认扫描夹具安全移除。
3. 仅当所有 N05 出口有实际证据时才更新为 `passed` 和推进 `next_goal`；否则保存未通过项、合法入口调整和恢复条件。
