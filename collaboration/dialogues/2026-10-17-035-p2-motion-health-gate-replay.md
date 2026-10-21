# P2 动态运动输入经定位健康适配器回放

- 用户目标：继续完成 `GOAL.md` 全部 A–H 与 P0–P6；按阶段记录证据，不能将单项演示当作项目完成。
- 约束：使用单 D435i 等效传感器包；真值不得进入 ROS 运行链，只能隔离记录与离线评估；不启动 PX4、不发布控制；用户已有 staged/unstaged/untracked 文件原样保留。
- 实施：取自 10/17 第二次匹配 VINS 二进制力驱动运行的 MCAP，生成全新 session/epoch；在固定 Jazzy 派生镜像中运行匹配 VINS 二进制、全仓 install 的 `uav_localization` 和只读 probe，再回放 `/clock`、左右红外图像与相机 IMU。
- 结果：10组有效配对后状态从 INITIALIZING 进入 TRACKING；记录386条优化和5087条传播输出，frame 属于本次 epoch，时间单调且数值有限。传感器包结束后，适配器约0.05秒转 LOST，原因 `imu_stale`，随后进入 LOCKED；剩余约23秒观察期间状态计数保持不变。
- 解释：这是带真实 ROS 进程的运动包回放，不是实时 Gazebo 运行。它补充了第二次物理校准与适配器跟踪/断流门控之间的连接；没有模拟静默视觉退化，也没有证明协方差或精度阈值。
- 状态：P2 仍 `in_progress`；P0/P1维持通过，P4进行中，其他阶段未完成。下一步继续验证 VINS 退化质量门控与剩余 P2 条款，再冻结 F 验收阈值。
- 证据：[progress/evidence/p2-motion-health-gate-replay.json](../../progress/evidence/p2-motion-health-gate-replay.json)；输入 MCAP 和详细输出位于忽略目录 `artifacts/runs/p2-localization-adapter-motion-20261017-01`，来源包见 `artifacts/runs/p2-force-motion-20261017-05`。
