# GOAL C 第二障碍布局快照门控诊断 #320

对话摘要：[2026-10-20-069](../../collaboration/dialogues/2026-10-20-069-p2-ego-dense-spline-second-layout-gate.md)

复用 #318 patch 0029 binary与同一goal/config，run-local移动两处障碍，形成第二布局。目标发送成功且MapStatus ready，探针收到2条spline；新增最终曲线校验没有拒绝日志。两份只读snapshot都因`depth_pose_gate_closed`拒绝，没有有效曲线地图对照。随后EGO因depth/odom freshness timeout进入`EMERGENCY_STOP`，规划轨迹未交给trajectory server/controller执行。

验证：`bash artifacts/runs/p2-ego-dense-spline-second-layout-20261020-320/run-container.sh`，probe状态`bspline_received`、snapshot请求2/2 gate关闭；无PX4、controller、trajectory server、truth或control topic。几何、日志、service响应和hash见[证据](../../progress/evidence/p2-ego-dense-spline-second-layout-20261020-320.json)。该run被排除为净空判断；同布局新epoch复测见#321。
