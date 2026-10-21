# GOAL F 里程计 QoS 与无目标地图复核 #248–#251

关联对话：[2026-10-20-027](../../collaboration/dialogues/2026-10-20-027-goal-f-odom-qos-multi-geometry-followup.md)。

本轮没有修改自维护 ROS 源码、PX4 或相机参数。只读检查 EGO `grid_map` 源码：depth/pose 占据路径以 `ceil(inflation/resolution)` 对三轴做方块膨胀；默认0.099/0.1 m为27个格偏移，0.482 m名义包络的几何下界为5步（最多1331次内层写入/占用源格）。另一 cloud callback 的垂直膨胀固定为1格，但当前 mapping adapter 不发布该 cloud。运行成本和净空尚未测量。新增四组 run-local 仿真产物并更正 #248/#249 的 flight_type 事后解释；新增汇总证据报告，更新 README、CURRENT、证据索引、GOAL checklist 和 P2 evidence list。P2 与 GOAL B/C/F 状态保持原值。

#248 的 `/localization/optimized_imu_odom` 话题 remap 正确，但它复用了旧 install：该二进制 SHA-256 为 `0e3ddac0…`，优化里程计仍为 BEST_EFFORT，而 EGO 是 RELIABLE。adapter 日志记录 QoS `RELIABILITY` 不兼容且 EGO 保持 INIT，因此该轮排除。#249 使用 install 节点源码 SHA `63e97862…`（与当前 source 相同），live graph 显示定位 publisher 和两个 EGO subscription 均为 RELIABLE；EGO 收到输入，但 `flight_type=2` 实际加载预设 waypoint 并进入 SEQUENTIAL_START，无外部跟踪控制器。

#250/#251 使用 `flight_type=1` 且没有发布目标；FSM 源码定义它为 MANUAL_TARGET。#250 在2.2墙秒以 `left_stale` 锁定。#251 保持 `WAIT_TARGET`，有效窗口内采到547条优化里程计、1,026组 EGO 深度／位姿、最大1,256点 occupancy cloud；单次固定尺度 SE(3) 轨迹 RMSE 为9.11 mm。箱体25点区域残差中位/P95为3.3/6.3 mm；圆柱35点为80.3/164.0 mm，57.1%在10 cm内。#251 初始 localization status 为 TRACKING，但终端状态没有记录，且主探针窗口结束后的 EGO 日志出现 stale odom/depth；只读探针位姿源龄 P95/最大0.627/1.641秒、墙钟接收最大间隔2.220秒。

验证：四轮 world preflight 均通过 `gz sdf -k`；容器均退出码0且清理完成；四轮离线 evaluator 均产出报告。`python3 tools/project_status.py` 为 PASS；`git diff --check && git diff --cached --check` 通过；JSON 解析和原始/源码 SHA-256 审计校验175项通过。运行脚本通过 `bash -n`。本轮没有源码改动，因此未重复 ROS 构建。报告明确排除错误 install 轮、预设航点轮及短时锁定轮的验收用途。

尚未测量碰撞接触、自由空间/未知空间、地图膨胀覆盖、目标跟踪、机体最小间距、制动距离或故障退出时延；没有冻结 `config/acceptance.json`，GOAL F 与正式 D/E 验收仍未通过。后续 #252–#254 已记录五步膨胀点云和地图下界观察；继续追踪 EGO 输入间隙，测试无控制器的 EGO 规划目标并改善圆柱覆盖，再进入净空阈值冻结。
