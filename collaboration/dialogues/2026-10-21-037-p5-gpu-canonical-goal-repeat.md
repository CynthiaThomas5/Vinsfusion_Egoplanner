# 任务对话摘要

- 日期与任务 ID：2026-10-21 / #037
- 用户目标与明确约束：继续推进 P0–P6 单 D435i 仿真导航；保护工作区已有修改；canonical PX4/VIO 接收龄和定位健康阈值不放宽；最终导航图不订阅 `debug_truth`；PX4控制设定点及OffboardControlMode仍由 `uav_px4_bridge` 独占发布；P5通过必须有完整证据。
- 已确认的决定：在GPU、canonical配置和3秒遥测龄门下重复#394零相对位移／零yaw目标，不改变健康门或控制路径。首次失效后按精确归一化代价匹配原始VINS遥测，避免按相邻时间戳误配。
- 运行结论：#397前置5秒稳定检查通过，动作派发；匹配VINS样本source stamp 26.700秒normalized cost=1.0412199，健康状态source stamp 26.740秒首次报告 `normalized_cost_exceeded`，action aborted；EGO有86条匹配READY轨迹样本，bridge最终landed/disarmed。越线帧特征数、tracks和solver状态仍有效。PX4 ULog观察到EV融合、GNSS aiding flags为零；项目ROS图没有真值输入。
- 解释边界：与#394成功后降落阶段越线、#395无控制静置和#396无导航目标悬停未越线相比，重复目标加强了轨迹活动相关性；尚未采集本次Ceres分组代价，不能确定由视觉、IMU、边缘化先验或其他差异触发。最大raw cost 4.6349发生在首次失效之后，不能当作触发值。
- 待办：用既有可选VINS诊断补丁建立run-local overlay，仅在首次cost越过1.0时输出分组代价，保持canonical源码、参数、健康阈值和控制出口不变；将该样本与goal、轨迹和health状态同时间线对齐。之后依据分组结果做单变量实验。P5仍未通过。
- 对应改动记录：progress/changes/2026-10-21-037-p5-gpu-canonical-goal-repeat.md
