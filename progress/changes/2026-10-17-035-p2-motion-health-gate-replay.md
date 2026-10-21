# P2 动态运动输入经定位健康适配器回放

- 任务 ID／日期：035／2026-10-17
- 对话摘要：[P2 动态运动输入健康门控回放](../../collaboration/dialogues/2026-10-17-035-p2-motion-health-gate-replay.md)
- 修改文件：新增 `progress/evidence/p2-motion-health-gate-replay.json`；更新 `progress/CURRENT.md`、`progress/milestones.json`、`progress/goal-checklist.json`、`progress/evidence/README.md` 与 `README.md`。
- 行为变化及原因：无运行时代码变化。用第二个匹配二进制动态力驱动包验证真实 VINS 和定位适配器串联；P2保持 `in_progress`，项目验收仍未完成。
- 验证类型：实际 ROS Jazzy 进程回放。输入 MCAP 只含 `/clock`、双目红外图像与相机 IMU；新 VINS session、新 epoch；只读 LocalizationStatus/Odometry probe。没有 Gazebo进程、真值 ROS 输入、mapping/EGO、PX4、控制或飞行。
- 命令与环境：`docker run --rm --network host --shm-size=1g -v "$PWD:/workspace" -w /workspace d435i-vins:dev bash /workspace/artifacts/runs/p2-localization-adapter-motion-20261017-01/run-container.sh`；image `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`；ROS domain 228；VINS binary SHA-256 与基准一致（`858e3566…`）。
- 结果：[P2 回放报告](../evidence/p2-motion-health-gate-replay.json)：10组有效配对后进入 TRACKING；386优化/5087传播输出，严格单调、有限、epoch frame 一致。包结束后以 `imu_stale` 转 LOST→LOCKED；锁定观察约23秒，状态接受计数不变。
- 验证命令：`sha256sum -c artifacts/runs/p2-localization-adapter-motion-20261017-01/source-sha256.txt`；`python3 tools/project_status.py`；JSON parse 与 evidence SHA-256 核验；`git diff --check`、`git diff --cached --check`。
- 局限：断流锁定证明 freshness/fail-closed，不证明图像退化或静默漂移识别；`covariance_valid=false`；健康策略仍是 PROVISIONAL。无PX4 EKF2融合、飞行、地图、规划或真实相机结果。
- 下一步：补足 VINS 静默退化/质量门控证据并核对剩余 P2 条款；完成后才冻结 F 的正式验收标准。
