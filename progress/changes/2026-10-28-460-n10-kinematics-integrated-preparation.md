# N10.3/#460 正常综合校准准备

对话摘要：[2026-10-28-460](../../collaboration/dialogues/2026-10-28-460-n10-kinematics-integrated.md)。

- 基于 #458 复制 run-local driver、观测器、离线评估器和冻结模板；新运行 ID 为 `n10-20261028-460-maxcnt220-kinematics-integrated`，不修改 #458/#436 归档。
- 沿用 #458 的 16 m 路线、VINS `max_cnt=220`、planner/spawn、动态箱体几何与时序、20 仿真秒保持、传感器采集及正常落地流程。
- 纳入 #459 已验证的 PX4 根模型来源修复，并把 `tools/sim_runtime.sh`、模型来源 evaluator 纳入运行前工具身份。实际 SDF 路径/SHA记录为离线证据，不作为目标或起飞条件。
- 跨运行评估参考改为 `artifacts/reanalysis/n10-20261028-438-reference-unification/n10-20261028-436-normal-map-halo-calibration/`；原始运行分开评估，不拼接 epoch 或数据点。
- 本次不做故障注入，不计 N15/N16 正式次数，不改控制参数、碰撞几何、验收阈值或运行拒绝逻辑。

## 启动顺序

1. `D435I_N08_MODE=execute D435I_N09_CONTACTS=1 D435I_N10_KINEMATICS=1 D435I_N10_CAPTURE=1 D435I_N10_CAPTURE_WALL_S=1800 D435I_N10_DEPTH_FAULT=0 D435I_PLANNER_CONFIG=config/components/mapping/n10_horizon5_speed040_yawcap010_compacttrace_calibration.json D435I_SPAWN_CONFIG=config/components/simulation/n10_long_range_spawn_minus8.json bash tools/project.sh sim n10-20261028-460-maxcnt220-kinematics-integrated`
2. 待容器写出 `stack-started` 后，先运行复制目录内 `prepare_prelaunch.py` 冻结本轮 runtime、VINS session、地图/planner与 PX4 读回身份；检查没有提交飞行目标。
3. 只有上述冻结完成后，运行同目录 `n10-runtime-driver.sh`，随后按独立安全终态读回与脚本评估结果收尾。

静态检查已执行：prepared `prepare_prelaunch.py` 的 Python 编译、driver 与 runtime shell 语法、40 项 observer/区间净空/总验收定向测试、项目结构检查均通过；跨运行 evaluator 用 #436 reanalysis 与 #458 原始归档做只读 smoke，正确保留运行身份差异并返回 `INSUFFICIENT`。SITL 尚未启动，运行结果待记录。
