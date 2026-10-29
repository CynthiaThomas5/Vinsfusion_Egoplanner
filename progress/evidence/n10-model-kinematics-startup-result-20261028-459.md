# N10.3/#459：瞬时运动观察器根模型来源验证

## 结论

**假设确认，启动诊断通过。** PX4 启动时使用 `PX4_GZ_MODELS/<model>/model.sdf` 的直接路径。此前 `PX4_GZ_MODELS` 指向源码模型目录，虽然 run overlay 已在 `GZ_SIM_RESOURCE_PATH`，PX4 仍加载不含观察器的根 wrapper。现在仅当 `D435I_N10_KINEMATICS=1` 且 N09 overlay 开启时，将该变量指向本轮 overlay；无观察器请求时仍用原始模型目录。

本轮没有运行 `mission`、发送目标、使能或解锁。PX4 的实际选中模型报告指向 `artifacts/runs/n10-20261028-459-kinematics-startup-diagnostic/n09-contact-models/x500_d435i/model.sdf`，SHA-256 `4d1e8f43394b2dc1ab9a5e26016489f04c5744cb491d149d75011c042e931cee`；与 overlay manifest 的生成 SHA 一致，根 SDF 中观察器插件恰好一个。Gazebo 话题 `/debug_truth/model_kinematics` 确认有发布者；5.10 秒只读采集中收到 854 个 `x500_d435i_0` 状态，元数据/数值错误 0、仿真时间戳严格递增、最大样本间隔 0.004 s。

结束前独立 ROS/PX4/bridge 读回：bridge `DISABLED`、`control_enabled=false`、`armed=false`、`landed=true`；PX4 arming state `1`（disarmed）、LandDetected=true；控制模式/轨迹设定点/车辆命令计数均为 0，任务/规划事件为 0。记录到 PX4 native preflight `pre_flight_checks_pass=false`、bridge reason=`px4_preflight_failed`，本轮未请求起飞，未增加项目拒绝逻辑。确认上述安全状态后 `project.sh stop` exit 0，容器 exit 0；没有项目容器遗留。

此结果只验证 observer 的实际加载与短窗口传输，不能替代完整导航任务的物理步 ledger，也不能单独证明连续净空。下一步需在单次代表性正常完整导航中复用 #458 路线和 `max_cnt=220`，采集从活动任务到落地的完整瞬时物理状态；不重跑故障类别或 N15/N16 正式矩阵。

## 改动与验证

- `tools/sim_runtime.sh`：observer 启用时将 PX4 根模型来源指向 run-local overlay，并生成 `n10-px4-model-source.json`（直接选择路径、SHA、插件数）；不改碰撞几何、控制和准入行为。
- `tools/debug_truth/kinematics_evidence.py` 与区间/总验收器：要求实际 PX4 选中 SDF 的路径、SHA 与生成 overlay 文件/manifest 一致；缺少或不匹配时离线报告不足。
- `PYTHONPATH=tools python3 -m unittest tools.test_n10_kinematics_evidence tools.test_n10_interval_clearance_bound tools.test_n10_acceptance`：40 项通过。
- `PYTHONPYCACHEPREFIX=/tmp/n10-459-pycache python3 -m py_compile ...`：通过。第一次直接 py_compile 遇到仓库已有 pycache 权限问题，改用临时 cache 后成功，未改权限。
- `bash -n tools/sim_runtime.sh`、`git diff --check`：通过。

原始运行输出：`artifacts/runs/n10-20261028-459-kinematics-startup-diagnostic/`。准备协议见[#459 protocol](n10-model-kinematics-startup-protocol-20261028-459.md)。N10 继续 `in_progress`，N10.3 仍待完整 ledger 与标准收敛。
