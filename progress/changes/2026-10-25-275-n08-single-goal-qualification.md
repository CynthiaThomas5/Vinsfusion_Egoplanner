# #275：单目标 N08 试验与候选降落准入

- 目标：按N08计划把普通单目标验收与用户另行发起的返航链分开，并给目标后落地建立raw-map候选几何准入。
- 已有基础：#260/#267/#273均有去程EGO目标和有效末端制动／停车测量；固定hold #212、compute-only #257可供受控对照；原runner把yaw／return后置动作纳入单轮总评。
- 当前假设：已有同run ground/airborne snapshots在去程目标附近有足够raw-ground平面支持候选降落；唯一主要变量是落点相对已准入home pad的0.6m水平偏移；判据沿用N05实际机体、地面拟合、raw分类及起降扫掠规则，不采用真值或完整世界地图。先对归档snapshot离线计算，结果决定实现接口。
- 允许修改：N08 runner/evaluator和相关测试、必要的候选下降／触地体素核验、Goal专用N08配置、changes/dialogue/CURRENT；不改GOAL验收值、N05 landed判定、unknown规则、0.12m/s向量门、0.15m/s水平watchdog、0.25m空间余量或5cm参考管道。
- 安全边界：复用候选地面只表示未来几何假设；PX4 landed状态只由实际反馈确认。候选落地区/停止体积未在同run新鲜raw map通过前不启用PX4 execute。
- 完成标准：单目标场景在目标处停车保持后独立降落，评估无需return action；候选降落证书对known floor / unknown / occupied / map-edge有定向验证；旧round-trip路径保持兼容；控制源/配置指纹与输入证据可追溯。
- 复盘：归档地图同时输出源点与+0.6m候选落点的ground-plane和逐阶段拒绝分类。若地图不支持，转入观测覆盖问题，不挪动试验落点或放宽N05门。
- 下一步：完成#275后继续B/C/D，建立取消停止边界与行为，再完成预算初版及同版本三次独立运行。

## 2026-10-26 实施与首轮静态验证

- 改动：`tools/run_n08_braking_trial.py`增加默认`single_goal`与显式`round_trip`，到达后在目标处fresh raw map检查候选hold／下降／contact，再要求实际bridge landed/disarmed；不自动发送return action。`tools/debug_truth/evaluate_n08_braking.py`按0.12m/s实际向量限制与原0.15m/s水平限制分别判定，并支持取消停止曲线事件指标。mission入口支持normal terminal stop与两种speed-window cancel calibration。
- 改动：`tools/n05_entry.py`及其测试新增预测地面候选下降／触地点积检查，不伪造`ground_confirmed`；`tools/n08_trial_gate.py`以home raw plane实际IMU离地高度投影候选落点。历史三图回放报告见[#277](../evidence/n08-candidate-landing-archive-audit-20261026-277.md)。
- 改动：`TrajectoryCancel`加`MODE_STOP_HOLD`，仅navigation的`caller_cancel`采用此模式；定位／地图／时钟等错误继续`MODE_ABORT`。EGO #0046按当前VIO速度提出前向停车目标，并让全曲线／末端hold继续经过已有raw-map freshness、identity和body certificate；planner不支持或证书失败仍走ABORT安全降落。候选停车距离为历史最大末端制动测量按速度缩放、加0.10m余量，试验范围有限，未声称普适下界。
- 第三方来源：EGO上游commit仍为`23a8d5a191711dd65633df689bd00f55d4dea8f9`，#0046接在#0045后；patch hash=`b1f9aa0d69eb1dc9637bc7de51942666fde9c7aab054124344987d6502629d82`。来源与序号写入`dependencies/sources.json`及`dependencies/patches/ego/README.md`。EGO planner source最终hash=`69ac8db5799984b7d557699a7fd1640807b30eb91cd66cba50d928e90e1a0ecf`。
- 验证：`bash tools/project.sh build ros`通过，17个ROS包；`bash tools/project.sh test`通过，333个unittest加navigation adapter integration；定向N05/N08映射、制动与落地用例39项通过；Python compile、`bash -n tools/mission_runtime.sh tools/project.sh`、patch `--dry-run`均通过。build/test不表示飞行通过。
- 未解：尚未在仿真验证`MODE_STOP_HOLD`真实EGO停车样条交接、PX4实际速度／停止／保持与落地。下一步新冷启动低速取消试验；结果不合格就记录FAIL并修复后重建，普通目标三次同版本重复暂不启动。
