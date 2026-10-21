# P2 匹配二进制 VIO 独立校准复测

- 任务 ID／日期：034／2026-10-17
- 对话摘要：[P2 匹配二进制独立 VIO 校准复测](../../collaboration/dialogues/2026-10-17-034-p2-repeat-calibration.md)
- 修改文件：新增 `progress/evidence/p2-repeat-calibration.json`；更新 P2 证据索引、`progress/CURRENT.md`、`progress/milestones.json`、`progress/goal-checklist.json`、`README.md` 和 `tools/project_status.py` 的下一步提示；完整输入、运行数据与日志保留在 `artifacts/runs/p2-force-motion-20261017-01` 至 `-05`。
- 行为变化及原因：没有运行时代码行为变化。新增同 VINS 二进制的第二次独立运动校准；状态检查器已从“重复校准”更新为剩余健康/退化门控和验收标准任务。P2 保持 `in_progress`。
- 验证类型：Jazzy/Gazebo Sim 8.14.0 容器内 live 仿真；D435i 等效模型由物理力/力矩激励；真值仅在调试记录器留存并离线评估。VINS 节点图确认订阅双目、相机 IMU 和 `/clock`；没有 truth subscriber、mapper、planner、PX4 或控制发布者。
- 有效运行：`p2-force-motion-20261017-05`；ROS domain 229、独立 Gazebo partition、新 epoch。使用 `p2-build-20261016` 的原 VINS 二进制，SHA-256 与 10/16 基准均为 `858e356677decfd0a4d88db1861a293ace7a91f7a3909333401b8f598fe8a010`。新 build 二进制另在 #04 运行，SHA 不同，单列交叉检查。
- 验证命令：`python3 tools/evaluate_vins_motion.py --motion artifacts/runs/p2-force-motion-20261017-05/motion.json --odometry artifacts/runs/p2-force-motion-20261017-05/probe/raw-odometry.json --output artifacts/runs/p2-force-motion-20261017-05/metrics.json`；容器内 `ros2 bag info .../input-bag`；`sha256sum -c artifacts/runs/p2-force-motion-20261017-05/source-sha256.txt` 与 repository-source 清单；`python3 tools/project_status.py`；JSON parse；`git diff --check` 与 `git diff --cached --check`。
- 结果：位置 RMSE0.02592 m、P95 0.04784 m、最大0.05463 m；姿态 RMSE0.716°；比力RMSE0.001876 m/s²；yaw-rate RMSE0.00004273 rad/s。742条优化、9763条传播输出、742条遥测，输出有限；输入MCAP 478.7 MiB，SHA-256 见证据报告。首轮匹配二进制位置RMSE0.02533 m。
- 排除运行：#01 驱动副本根路径错误；#02 wrapper 输出目录硬编码；#03 漏掉 VINS `__ns`，轨迹探针无法订阅 epoch 输出；均保留并写明原因，不纳入精度结果。#04 是不同二进制，仅作为单独交叉检查。
- 局限：理想仿真台架，不是机载相机/真实飞行验收；正式阈值未冻结；本轮不含健康适配器、地图、EGO、EKF2、PX4、SITL 飞行或实机。VINS raw `initialized`/`solver_usable` 在该轨迹期间保持 true，不能证明其可检出漂移或退化。
- 下一步：继续 P2 健康/退化门控的定量验证，核对剩余 P2 失败注入要求；满足条件后先冻结 F 阈值，再开展正式 D/E 运行。
