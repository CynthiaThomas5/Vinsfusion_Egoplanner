# N08 #321：当前版本 caller-cancel 停止与保持通过

## 结论

冷启动 run n08-cancel-highspeed-prescan-20261026-321 完成单程运动中取消试验。Native flight 结果为 PASS，独立 N08 braking evaluator 的 passed 为 true。goal 模式为 single_goal，trial_kind 为 motion_cancel；action_goal_sent=true，return_action_sent=false。飞行到达终点前按 0.04–0.06 m/s PX4 水平速度窗口取消，EGO 发布经证书检查的替代停止样条，飞机停止并保持，随后在终点落地并解除武装。

本次补全了当前构建下的取消→停止样条→实际减速→保持链。它是 motion_cancel 试验，不计入正式出口要求的三次普通 terminal_stop 到达。

## 关键测量

- PX4 取消触发水平速度：0.04014 m/s；EGO 参考速度：0.05848 m/s。
- 取消请求至实际停止的独立真值路径长度：0.30407 m；候选前向停止走廊为 0.50 m。取消时剩余已准入走廊为 0.55477 m。
- 取消至持续减速判据响应：2.876 s。该量包含闭环响应和系统滤波，不能解释为纯通信延迟。
- 实际峰值向量速度：0.08585 m/s，低于本试验 0.12 m/s 约束；独立最大跟踪误差 0.08788 m，低于 0.15 m watchdog。
- 取消后满足水平速度不超过 0.03 m/s、垂向速度绝对值不超过 0.05 m/s 持续 1 s；随后 3 s 保持通过。参考停车开始至实际停车距离为 0.19646 m；参考零速后的残余位移为 0.02904 m。
- 替代停止 spline 已认证，旧轨迹未恢复，bridge 在停止和保持期间保持 ACTIVE。终点降落前及最终候选检查通过。

减速度分位数是本有限样本的实测描述，不宣称为保证下界。0.50 m 是当前低速前向取消协议使用的候选走廊长度，既有 N05/N06 body、uncertainty 和 tracking 门限未变。

## 准入与安全收尾

N05 支撑扫描完成，夹具已脱离且从 Gazebo 移除；释放后和任务内在线／离线入口检查对同一 epoch/map 身份一致准入。解锁前与空中 full-body 前向走廊、起点／终点 hold 及终点着陆候选均通过。任务期间连续性、时钟、唯一 bridge 控制发布者和无真值控制检查全部通过。飞行后独立读回为 bridge LANDED/control disabled、PX4 disarmed/landed，OffboardControlMode、TrajectorySetpoint 和 VehicleCommand 样本数均为 0；车辆保持未解锁，项目容器退出码 0。

mission wrapper 在 native 任务已完成后因固定镜像缺少可选 matplotlib、但仍无条件传入 --plot 而返回退出码 1。保留该 wrapper 状态；随后在同一镜像去掉绘图选项单独执行 evaluator，结果 passed=true。未改 wrapper，也没有把该缺陷冒充成飞行失败或静态测试通过。

## 冻结身份与产物

该次 runtime-contract 内部 SHA256 为 75aaa541f7684b38fe0805b958e029fa21f8c6dd6ab00d2ebe1fae92c7e8a772。目标配置 SHA256 为 b2aacac43b8e321806387471b6f62e40bbc5c6d32d23b15b314157bed1913108，planner 配置 SHA256 为 f8216372bdeda44f02b891381adbdb806c8866f252698dda87c29d14a6e29cce。后续普通目标重复使用同一源码、install、配置、模型、镜像和 observer 身份；记录文档不会改变 runtime manifest。

主要原始产物位于 artifacts/runs/n08-cancel-highspeed-prescan-20261026-321/，包括 flight.json、n08-braking-evaluation.json、runtime-contract.json、n05-run-summary.json 及 post-mission-independent-live-readback.json。此报告只引用原始运行，不更改原文件。
