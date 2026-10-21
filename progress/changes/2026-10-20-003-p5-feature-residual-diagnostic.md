# P5 VINS 逐特征视觉 residual 诊断（#203）

对话摘要：[2026-10-20-003](../../collaboration/dialogues/2026-10-20-003-p5-feature-residual-diagnostic.md)。轻量证据：[逐特征 residual 报告](../evidence/p5-vins-feature-residual-diagnostic-20261020-203.json)。

## 变更

- 新增 `dependencies/patches/vins/0006-feature-residual-diagnostics.patch`，只用于 #203 run-local VINS；不加入 `dependencies/sources.json` 标准来源补丁链。基于固定 VINS commit、项目0001–0005及 #181 run-local图像/分组代价计时 overlay。构建前 dry-run 检查通过，实际 patch 回放后的 estimator SHA 与 manifest 一致。
- feature diagnostic 环境变量默认关闭；启用后，在首次 normalized_cost≥1.0 样本上一次性读取所有视觉 residual blocks，按现有 Huber loss 统计 track cost、保存 top20 feature 与 observation 的时间戳、像素坐标和 residual。`FOCAL_LENGTH/1.5` 缩放后的残差乘1.5作为近似 pixel-equivalent 值，不作为独立像素真值。
- #203 的 run-local harness 保留 `visual_feature_residuals`；新增 VINS隔离构建脚本、源码补丁 manifest 与 PX4 landing timeline。

## 验证

- `patch --dry-run` 与后续 patch replay 通过；run-local Jazzy `camera_models`/`vins` 新 build/install 2/2通过。
- SITL 脚本本次自维护包构建6/6，package prefix 确认桥接和 VINS 均使用 run-local install；导航目标通过稳定门并发送，无真值输入或 debug_truth 订阅。
- #203 质量门中止后 landed/disarmed；现有 direct-current PX4 时间戳路径无错误。PX4 ULog里无dropout、EV position/yaw/velocity融合各21/39、GNSS aiding零，battery warning/fault零。触地后有约0.78秒 DESCEND/failsafe，不能计P5通过。
- 首次越线 telemetry 为 normalized_cost=1.08720、1952总 residual dimensions；视觉组占88.977%。860个视觉 blocks的重新计算 Huber cost 与组 cost相同，评估耗时0.2313 ms。20个最高残差观测集中于图像左下区域且 horizontal residual 同向；没有图像帧、内容标签或真值可判因果。
- 对 bridge 时间映射、控制、VIO profile及帧转换共57项测试通过；`python3 -m py_compile`、`python3 tools/project_status.py` 与 `git diff --check` 通过。构建与 SITL 细节及哈希见轻量报告。

## 局限与下一步

此运行说明视觉 residual 有空间聚集，不证明图像边缘、标定、匹配或飞行运动是原因。下一步在只读 observer 中保存越线时刻最近的左右图像并标注残差端点；observer 不发布控制、不订阅 truth，也不进入最终组合。`normalized_cost=1.0`、65 ms future 容差及 PX4 freshness 门保持不变。
