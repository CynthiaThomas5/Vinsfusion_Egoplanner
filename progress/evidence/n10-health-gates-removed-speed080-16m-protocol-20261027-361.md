# N10.3 #16m：移除项目自定义定位门限后的 16 m 校准协议

初版在 SITL 启动前冻结；首次 mission goal 发送前做了 driver 文件名修正并重冻。当前状态：**首个 goal 前已修订冻结**。本次是 Goal 完成模式下 N10.3 的单次诊断校准，不构成 N10.3 或 N11–N16 的通过证据。

## 假设与唯一运行变量

在同一个单 D435i、16 m/3D/yaw EGO 任务中，移除本项目自加的 VINS 质量与定位/里程计回执龄拒绝后，任务可否完成并持续记录 raw VIO、地图时效、跟踪、接触、PX4 和 600 仿真秒保持数据。

唯一影响飞行运行的变化是定位质量/新鲜度门控：#357 通过运行时旁路跳过旧门限；#361 从运行路径删除这些门限，指标只观察和记录。EGO 规划参数、起点、目标、场景、PX4 参数、官方碰撞策略和观察器与 #357 保持一致。此次也清除了航线配置里未被执行器使用的 `acceptance_calibration_limits` 旧字段，并移除了执行器对该死字段的空类型检查；此前这些数字没有执行任何运行拒绝或通过判定。

## 保留的约束

- VINS epoch/会话身份、消息字段与坐标合法性、每流时间戳单调、ROS 时钟单调和唯一已识别 VINS 发布者仍作为会话/接口完整性约束。
- `official_ego` inflated-occupied 碰撞判定、地图身份/新鲜度、唯一 PX4 控制发布者及 PX4 桥控制/看门狗保持有效。
- 真值仅供只读离线评估；接触观察覆盖不改变碰撞几何。
- normalized cost 的历史 1.0 仅用于离线观察对照，不作为运行门限或通过门槛。位置、yaw、跟踪、地图龄、净空和制动均报告量测，不在本次人为设阈值。

## 首次 goal 前的 driver 修正

第一次启动 driver 时，它在只读 preflight 前因 runtime contract 当前快照文件名不一致而退出。没有发送导航目标或 enable 请求，`flight.json` 和 `flight-probe-ready` 均未创建。随后 3 秒独立 PX4/bridge readback 确认 DISABLED、已落地、未武装、控制关闭、控制样本为零，见 `artifacts/runs/n10-20261027-361-quality-gates-removed-speed080-16m/setup-preflight-readback.json`。已修正为读取运行时实际写出的 `n09-runtime-contract-current.json`；runtime contract 与航线/飞行参数未变。失败尝试记录：`artifacts/runs/n10-20261027-361-quality-gates-removed-speed080-16m/driver-preflight-attempt-01.log`。当前 driver 哈希在本协议修订中重新冻结。

## 冻结任务与判据

- EGO：max velocity 0.8 m/s/轴、max acceleration 0.25 m/s²/轴、planning horizon 5 m。
- 路线：一个 +16.0 m ENU / +0.10 m / +0.20 rad 目标、3 s 驻留、目标后 ACTIVE 保持 600 仿真秒，再由 PX4 桥降落。
- 诊断样本要求：任务动作及真值到达驻留完成、600 秒保持完成、真值/定位/规划/bridge/contact/source 时间观察器覆盖终态、无禁止接触，且独立 PX4/bridge 读回确认已落地、未解锁、控制关闭和零控制样本。
- 失败/中止会原样保留并分析原因。通过也只说明该诊断样本完整，不冻结正式误差或安全限值。

## 版本和执行命令

- Runtime contract：`fdf104f5bd7b733128656fc4736af001f9ecdcbe1d93de123b41c7974a511a2f`（665 个文件）。
- Driver SHA-256：`f6a219a5e2a780bfe50cd8277953dca082abfbd827eb7559d69c651bf818587f`；analyzer SHA-256：`8243ec0f569e930e4c59fa420f10c1522def1515f3a872cdfe62e895a18b8773`。
- EGO profile SHA-256：`0f92519ded6f367387998f01e19a27e270b94c7571e12fbe5b80f82b8ed7473e`；goal profile SHA-256：`0e275927089a9d04810d483fc6634717d6f7fcd15472a508601cbd5790600f00`。

启动：

```bash
D435I_N09_CONTACTS=1 D435I_PLANNER_CONFIG=config/components/mapping/n10_horizon5_speed080_calibration.json D435I_SPAWN_CONFIG=config/components/simulation/n10_long_range_spawn_minus8.json bash tools/project.sh sim n10-20261027-361-quality-gates-removed-speed080-16m
```

SITL 堆栈出现 `stack-started` 后，在该项目容器内运行冻结 driver：

```bash
docker exec d435i-n10-20261027-361-quality-gates-removed-speed080-16m bash /workspace/artifacts/n10-prepared/n10-20261027-361-quality-gates-removed-speed080-16m/n10-runtime-driver.sh
```

仅在 driver 生成独立 PX4/bridge 终态读回并确认可安全停止后关闭本项目容器：

```bash
bash tools/project.sh stop n10-20261027-361-quality-gates-removed-speed080-16m only after the independent PX4/bridge terminal readback in the run driver confirms safe_to_stop_project_container=true
```

机器可读协议：[JSON](n10-health-gates-removed-speed080-16m-protocol-20261027-361.json)。Runtime prelaunch snapshot：[JSON](n10-health-gates-removed-speed080-16m-runtime-contract-prelaunch-20261027-361.json)。运行目录：`artifacts/runs/n10-20261027-361-quality-gates-removed-speed080-16m/`。
