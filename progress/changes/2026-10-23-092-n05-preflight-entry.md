# #092 N05 起降入口与自身过滤

对话摘要：[N05 任务摘要](../../collaboration/dialogues/2026-10-23-092-n05-preflight-entry.md)。

## 目标与执行模式

- Goal 完成模式；用户指定范围 N05；依赖 N01、N04 均已通过。
- N05.1 已完成：冻结当前 SDF 包络、测量项和初始空间预算，并定义接触／相位边界。
- N05.2 已完成实现：同一 raw-map 几何检查器用于在线快照及归档回放；N05.3 正在收集两个布局的完整模型支架扫描证据。

## 实施与产物

- 新增 `config/components/navigation/vehicle_envelope.json`：唯一 IMU 参考坐标、x500+D435i SDF 来源哈希、几何包络、N01/N04 误差项、线性合成的不确定性预算、raw 分类语义、地面接触与预扫描转移条件。
- 修改 `config/components/mapping/ego_planner.json`：`ground_height_m` 从 `-0.15` 调为 `-0.65`，使 plan_env 当前裁剪范围包含相机 IMU 参考系下机体下缘及预算扩张区。配置哈希同步锁入包络文件。
- 新增 `tools/n05_entry.py`：解析锁定 SDF 碰撞体与旋翼扫掠；拟合当前 raw occupied 地面；按 TAKEOFF_CONTACT、ASCENT、HOLD、DESCENT、LANDING_CONTACT 验证误差扩张后的包络；越界、未知、占据、姿态异常、身份／时间异常均 fail closed。接触例外只针对已观测地面平面、名义机体足迹及指定接触阶段，不改写地图。
- 新增 `tools/check_n05_entry_live.py`、`tools/evaluate_n05_entry.py`：通过 `/mapping/get_occupancy_snapshot` 执行只读在线检查、保存原始占据快照，并由归档输入独立回放同一判据。
- 新增 `tools/probe_preflight_scan.py` 的两个 N05 布局配置及 `--hold-for-live-check` 流程：DISARMED 支架上扫描当前完整 x500+D435i 固定相机；等待在线检查后再安全回收外部夹具。新增 `tools/run_n05_preflight_layout.sh` 与 `tools/summarize_n05_layout_run.py` 管理单容器、前后检查、哈希、夹具状态和报告。
- 新增 `tools/test_n05_entry.py`：覆盖几何／预算锁定、free 通过、unknown／occupied 拒绝、接触状态限制、unknown 不被清除、越界／倾斜拒绝及无起点豁免。
- 按 `n05-20261023-wall-r02` 的 raw snapshot 发现 ground-plane z 上界将搜索阈值按 voxel center 直接截断，排除了与边界相交的 −0.10 m 地面格。对 0.10 m 栅格，上界改为物理界限加半个 resolution；同一快照命中 128 个 raw occupied voxel、XY span 为 1.0×1.6 m、拟合 p95 residual 约 `1e-16 m`、slope 约 `7.5e-17`。该修正不触碰 occupancy，后续完整机体 sweep 的 unknown 仍拒绝。
- `tools/evaluate_n05_entry.py` 现兼容早期拒绝分支并验证／默认 entry schedule 参数；`check_entry_schedule` 的早期拒绝结果保留 hold/sample 参数，便于独立归档复算。

## 静态验证

- `PYTHONPYCACHEPREFIX=/tmp/codex-n05-pycache python3 -m unittest tools.test_n05_entry -v`：当前 8 项通过，包括 voxel-boundary ground fit 和拒绝结果回放参数。
- `python3 tools/audit_vehicle_envelope.py`：SDF 解析通过，方向不变旋翼扫掠半径 `0.4819358707 m`。
- 配置中所有 SDF／planner 源哈希：通过。
- N05 Python AST 解析及 `bash -n tools/run_n05_preflight_layout.sh`：通过。
- 主机不含 ROS `rclpy`；在线命令只在固定仿真镜像执行。

## 允许运行范围与完成标准

- 仅允许 Gazebo SITL 中 DISARMED 支架扫描和只读地图查询；不启用 Offboard、不发布航点／控制、不连接实机。
- 至少两个布局的在线快照、离线回放、状态／身份一致性、unknown／覆盖不足拒绝和夹具安全回收都有产物；未武装扫描不计飞行通过。
- 线性误差合计是观测样本的暂定初值，不是硬误差界；夹具也未飞行认证。N05 全部出口未获证前保持 `in_progress`。

## 当前结果与下一步

- N05.1、N05.2 的实现与本地验证已完成。
- `n05-20261023-wall-r01` 在创建夹具前停止，暴露桥状态 QoS 不匹配；检查器改为 reliable/volatile。`wall-r02` 完成 199 s DISARMED 支架扫描，但后检暴露 voxel-boundary ground-fit 问题和独立 evaluator 的早期拒绝字段问题；r02 留作旧算法诊断。
- 当前版本 `wall-r03` 完成全部 12 个扫描阶段。前后快照均通过独立回放复算，并因 full-airframe raw unknown 拒绝；epoch/map_id 连续。runner 报告 remove service 未确认，但 detached 状态和 `gz model --list` 证明 fixture 不在场，PX4 桥为 DISABLED／disarmed／landed；随后通过 `tools/project.sh stop` 停容器。已生成诊断一致性报告，诊断流程通过不代表准入通过。
- `corridor-r01` 同样完成全部 12 个扫描阶段；前／后 attached 快照的准入结果均为 raw unknown、在线离线一致，夹具由当前 runner 确认 detached 和从模型列表消失。释放后 2 秒健康确认发现 localization receipt/state 暂时不满足，说明 attached 后检不能替代 released 后检查。
- 已把专用 `n05-post-release` live snapshot + replay 接入运行器。扫描器在完整 coverage 后若只于释放后健康确认报错，必须仍确认扫描完整、夹具 detached 且模型已移除，才继续专用 released admission；该命令若无法获取快照，会写 fail-closed structured refusal。汇总单独报告 prescan transfer gate，不将拒绝解释为起飞通过。
- 新 runner `wall-r04` 完成 12 阶段，attached 后检因 raw unknown 拒绝；map identity 连续。释放后 checker 120 秒未收齐 localization/map/bridge/odom/clock，保存 fail-closed 结构化错误；同一时间段 `vio.log` 记录 `mapping gate closed: telemetry_stale`，扫描清理报告 fresh DISARMED 状态接收龄越界。关联哈希和解释见 `artifacts/runs/n05-20261023-wall-r04/n05-post-release-runtime-correlation.json`。wall r04 的 transfer gate 明确未通过，夹具移除已确认。
- 当前 N05.3 下一子项：用更新后的检查器以 `corridor_box_column`（r02）复测，并记录缺失状态的具体 topic、释放后 raw snapshot 或拒绝。此运行用于第二布局的 transfer 证据，不会清除未知空间。

## N05.3 / N05.4 完成记录

前述 N05.3 “下一子项”是当时计划，结果由本节更新；验收原文未变。

- 离线定位了完整 scan 后 HOLD 包络仍有 324–338 个 unknown，主要 z 范围为 0.8–1.2 m；旧 coverage profile 的支架平台高度为 0.6 m。设定唯一实验变量为平台高度提升至 fixture SDF 上限 1.0 m，路径、持续时间、地图判据和误差预算保持不变。`probe_preflight_scan.validate_profile(..., "coverage")` 静态验证通过，仍为 12 个有界阶段。
- `wall-r05` 完成 12 阶段扫描及释放后检查。HOLD 最大 unknown 从同布局旧 profile 的 338 降至 163；TAKEOFF_CONTACT 仍有 498 个 unknown。attached-after 与 released-after 使用同 epoch/map_id，位姿变化 `0.000468273 m`，在线／离线同为 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`，`transfer_gate_passed=false`。模型已移除，扫描容器 exit 0。fixture worker 在 detach 后的 2 秒 freshness 确认返回错误，但 wrapper 仍依据已完成扫描、安全移除证据执行独立 released check；摘要的 `diagnostic_pass=true` 只表示诊断身份、回放和清理一致。
- `corridor-r03` 使用相同 1.0 m profile，在 8/12 阶段后 VINS `normalized_cost_exceeded`（1.0994866）；没有 prescan-ready 或 released admission。scanner 的 safe cleanup 返回零位、detach 并收到 Gazebo remove ack，模型列表确认 fixture absent；PX4 记录保持 DISARMED，项目容器退出 0。此健康失败未重试或放宽门限。
- `corridor-r02` 0.6 m profile 旧试次在 stage 10 触发 `normalized_cost_exceeded`（1.0206328）。recovery helper 使用 736 个 Gazebo fixture joint target 将支架回零并 detach；Gazebo model list 确认 fixture absent。恢复脚本末尾新鲜状态确认失败，但紧接着的独立 ROS 查询确认 bridge `DISABLED`／disarmed／landed、PX4 `arming_state=1`，容器随后以 exit 0 停止。新报告 `artifacts/runs/n05-20261023-corridor-r02/n05-recovery-followup-verification.json` 保存复核和原恢复报告 hash，旧 monitor marker 已解除。
- 对两布局的 0.6 m 完整扫描 `wall-r03`、`corridor-r01`，before 与 attached-after live 检查的五个阶段都因 raw unknown 拒绝，离线 archive replay 与在线一致；epoch/map_id 在各 run 内不变。`wall-r04` 的 released check 等待 120 秒后因完整状态集合缺失而 fail closed，同期 VIO 记录 `telemetry_stale`。
- 更新 `docs/running.md`：N05 diagnostic pass 不等于 takeoff admission；缺失／过期数据、VINS 失效、identity／pose discontinuity 或任一 phase refusal 时保持 PX4 DISARMED／桥 DISABLED，不发起飞目标，不清未知、不使用任意起点，也不以 `./start.sh fly` 绕过。
- N05 状态 `passed` 的范围是“fail-closed 入口规则、两布局 online/offline 一致性及 no-go 过程经验证”；它不授予起飞资格。机器可读和人工证据为 `progress/evidence/n05-entry-20261023.{json,md}`。N05 通过后依赖满足的下一项是 N06，本轮没有执行 N06。

验证：N05 入口／支架／恢复测试此前通过 17 项；本轮没有 Python 源码变化。本轮 coverage profile validator 通过。两个旧 profile 布局的 SITL 扫描完整；wall-r05 released admission 完整且拒绝 unknown；corridor-r03 保留 VINS 健康门失败并安全清理。无 Offboard、目标、飞行或实机运行。
