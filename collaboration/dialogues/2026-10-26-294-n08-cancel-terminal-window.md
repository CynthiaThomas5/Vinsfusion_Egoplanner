# N08 #294：EGO终端命令高频窗口判定

## #293运行结果

N05 6/6扫描、post-release online/offline、独立 disarmed/landed readback、40秒 preflight、mission current-area 和起飞前 map/landing admission 全通过。实际 caller-cancel在 PX4 0.0403m/s、EGO reference 0.0582m/s触发；action三字段正确，轨迹1由已认证轨迹2替换。新的 native terminal判据仍timeout，run为FAIL；未增加资格次数。独立读回显示 bridge LANDED/control disabled、PX4 disarmed/landed、控制输出0，项目容器停止。

诊断确定：轨迹末端后 EGO稳定发布零导数 READY 命令，约每8ms一条；runner只检查最新两条，却要求二者相隔50ms，故无法认定终端保持。PX4本地速度样本曾连续21.032仿真秒满足原停止门，但native正式3秒hold未记录，stop后 landing admission/command没有执行。

## #294修复

终端判据改为检查覆盖最近至少50ms的完整命令窗口，保留终点稳定、零导数和各身份约束。新增高频稳定通过及窗口中存在运动则拒绝的回归。`bash tools/project.sh test`为356项通过，navigation-adapter integration通过。下一步是全新冷启动#294重新完成N05与全部任务前门，再测同一 motion-cancel；N08仍in_progress。
