# 修改与验证记录

- 任务 ID／日期：#036 / 2026-10-21
- 对话摘要：[任务摘要](../../collaboration/dialogues/2026-10-21-036-p5-gpu-canonical-hover-diagnostic.md)
- 修改文件：新增 #393–#396 run analysis、manifest与轻量证据；为 #392–#396 建立 evidence index 与 P5 milestone 链接；更新 README、GOAL、CURRENT，并新增对话／改动记录。所有仿真日志、回执CSV、PX4 ULog与运行脚本保存在各自 `artifacts/runs/` 目录。
- 行为变化及原因：没有canonical代码、配置或任务阈值变化。#392 CPU配对run测得RTF 0.2898，3秒门失败；#393 GPU配对run RTF 0.6238并通过5秒稳定门。#394在相同canonical门下完成零相对位移／零yaw目标，但之后 `normalized_cost_exceeded` 导致安全降落。#395无控制额外观察45秒仍TRACKING；#396无导航目标定点悬停30秒并安全着陆，未复现cost越线。上述运行把问题范围缩到目标／轨迹活动相关，但尚不能证明因果。
- 验证类型：容器构建、控制关闭SITL诊断、门控导航smoke、受控悬停SITL、PX4 ULog离线审查。
- 命令与结果：#393–#396运行脚本 `bash -n` PASS；每轮 `colcon build --packages-up-to uav_px4_bridge` 6包PASS；#393、#395无服务／目标；#394 action PASS并最终landed/disarmed；#396 30秒hover PASS、无目标／PositionCommand并最终landed/disarmed。control topic publisher counts均为1；项目ROS topic与bridge订阅图没有 `debug_truth`。配置哈希保持 `bbc8a647742a4d0ad68b278017bfcd964b28503d8ba78fc9ee15a28c630356cf`，canonical桥接源哈希保持 `08918139cec607da2b3e8cd10ac28a84f91f5d61af9f61bbe497d125997a5a78`。
- 证据及解释：[CPU基线 #392](../evidence/p5-px4-vio-telemetry-clock-paired-diagnostic-20261021-392.json)、[GPU门控 #393](../evidence/p5-px4-vio-gpu-canonical-paired-gate-20261021-393.json)、[目标smoke #394](../evidence/p5-px4-vio-gpu-canonical-smoke-20261021-394.json)、[无控制长时观察 #395](../evidence/p5-px4-vio-gpu-canonical-idle-observation-20261021-395.json)、[无目标定点悬停 #396](../evidence/p5-px4-vio-gpu-canonical-hover-20261021-396.json)。#394 ULog中EV position/yaw/height/velocity各24/36条状态标志为真；GNSS fusion flags全零；ULog内部包含groundtruth dataset但没有接入项目控制或定位。GPU把稳定门从失败改为通过的证据仅适用于本机与本负载。
- 未验证与 PROVISIONAL：#394的目标保持并非障碍导航，也没有机体包络净空或真值误差限值；#394 cost越线的原因没有被隔离。#395/#396单轮未越线，不能独立证明EGO轨迹因果。没有重复冷启动、多障碍布局、故障注入或十分钟负载证据。P5保持 `in_progress`，最终A–H状态不变。
- 下一步：在同一GPU profile、canonical 3秒门与无真值运行图中重复#394零相对位移目标，记录目标开始／成功、READY轨迹、首次cost越线及bridge landing时间；如复现，再区分目标轨迹与任务状态切换。
