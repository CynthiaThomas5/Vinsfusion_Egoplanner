# P5 GPU canonical 零相对位移目标独立复测 #397

- 任务 ID／日期：#037 / 2026-10-21
- 对话摘要：[任务摘要](../../collaboration/dialogues/2026-10-21-037-p5-gpu-canonical-goal-repeat.md)
- 修改文件：新增 #397 run-local 分析／manifest 与轻量证据；更新 P5 证据索引、里程碑证据列表、README、GOAL、CURRENT；新增对话与改动记录。SITL、ULog、构建日志、遥测轨迹和run-local源码副本保存在 `artifacts/runs/p5-vio-px4-gpu-canonical-goal-repeat-20261021-397/`。
- 行为变化及原因：canonical源码、参数、3秒遥测龄门和1.0定位质量门均未改。GPU run通过5秒PX4/定位稳定门后派发零相对位移／零yaw目标；VINS在source stamp 26.700秒报告normalized cost=1.0412199，定位状态于26.740秒首次无效，action因 `localization_normalized_cost_exceeded` 中止，bridge最终LANDED/disarmed。cost匹配的VINS样本包含65个输入特征、63个双目特征、56条continued tracks、44条long tracks、1856 residual components，solver_usable=true。前后样本cost为0.581701和0.734996，故不是特征数量骤降的直接证据。
- 验证类型：GPU SITL零位移目标重复、VINS健康与轨迹时间线对齐、PX4 ULog离线检查、隔离／控制发布者检查。
- 命令与结果：运行脚本 `run-px4-vio-gpu-canonical-goal-repeat.sh` 在固定 `d435i-vins:dev` 镜像完成6个自维护包构建；RTF=0.64647，0次/秒钟回退，64点拟合窗口完整值1.329646–2.340117 wall/sim，配置界为0.1–10。5秒稳定门通过，action发送且在健康门触发后中止；87条PositionCommand中86条与READY轨迹匹配，最终landed/disarmed。PX4 ULog `EKF2_EV_CTRL=15`、`EKF2_GPS_CTRL=0`，EV position/yaw/height/velocity flags各40样本中23次为真，GNSS aiding flags全零。图中无 `debug_truth` ROS topic或bridge truth订阅；项目节点未使用ULog内部groundtruth dataset。control topic各只有一个publisher，bridge为唯一控制发布者。
- 证据及解释：[运行证据](../evidence/p5-px4-vio-gpu-canonical-goal-repeat-20261021-397.json)。VINS原始遥测按normalized_cost精确匹配首次health invalid值，并保存前后样本；首次失效与raw VINS源时间相差约40 ms，不能把邻近status stamp当作同一帧。#394目标在成功后降落阶段越线；#395 no-control长观察及#396无目标悬停未越线；#397目标重复仍在动作中越线。这支持关联但不证明因果，首越线样本的Ceres分组贡献尚未采集。
- 哈希：canonical桥接源码`08918139cec607da2b3e8cd10ac28a84f91f5d61af9f61bbe497d125997a5a78`、canonical配置`bbc8a647742a4d0ad68b278017bfcd964b28503d8ba78fc9ee15a28c630356cf`未变。run-analysis SHA256 `c3471faa94f2977478ae0d09d679469012ec7d8657f27bc9e786732625aef6db`；run-manifest SHA256 `0f93c8fdd58b59af074b309bdab8547e357d74890fcfb1d0fc5609496e4af1a9`。
- 未验证与PROVISIONAL：没有Ceres残差组归因、重复冷启动、障碍绕行、机体净空或定位真值误差评估；单轮关联不能证明EGO轨迹导致cost越线。P5维持 `in_progress`。
- 下一步：沿用已有的可选VINS诊断补丁，在run-local overlay启用首次quality threshold crossing时的边缘化、IMU、视觉cost分组输出，复跑同一目标与GPU配置；不修改canonical健康门或控制路径。
