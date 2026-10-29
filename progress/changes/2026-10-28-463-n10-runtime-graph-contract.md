# N10.6/#463 重建后任务入口回归

- 在 #462 clean install 上运行项目规定回归：596 项单测、导航适配器集成、official EGO policy probe 均通过。首次三项缺归档 SDF 夹具；核对原归档 SHA 后，只把该 fixture 放入隔离 candidate 的测试数据目录，重跑全套通过。
- 用 PX4/ROS fresh start 检查 3D/yaw waypoint 的图契约时，N09 wrapper 要求 `/navigation/ego_goal` 只有一个 subscriber；实际是 planner 与 PX4 bridge 两个接收端，且 N10 冻结记录也要求两者。wrapper 在目标提交前 exit 14。
- 停止前独立读回 PX4 disarmed/landed、bridge DISABLED/control disabled；无 goal、无 offboard enable、无起飞。项目 stop 正常退出，未使用紧急 disarm。
- 修复 `tools/n09_runtime.sh` 与 `tools/run_n10_cancel_calibration.sh` 的计数契约：仍检查一个 supervisor publisher、精确两个已知接收节点和唯一 bridge 控制所有权，只把期望订阅数更正为2。
- 验证：`bash -n`、`git diff --check`、`python3 tools/project_status.py` 通过。因为运行身份文件变化，#462 clean build 不再是最终候选；N10.5 需针对修复后源码重做。
- 证据：`progress/evidence/n10-rebuild-regression-20261028-463.md` 和 `.json`。下一步 #464：修复源码的隔离导出和全新 ROS/PX4 构建；之后重新做 N10.6 全套回归及代表性 PX4 任务。
