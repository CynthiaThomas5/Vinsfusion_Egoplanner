# P5 run-local 各向异性 feature filter 实验（#207）

对话摘要：[2026-10-20-007](../../collaboration/dialogues/2026-10-20-007-p5-anisotropy-filter-experiment.md)。轻量证据：[过滤器与零偏移目标报告](../evidence/p5-vins-anisotropy-filter-zero-offset-20261020-207.json)。

## 变更

- 新增 `dependencies/patches/vins/0008-feature-anisotropy-filter-experiment.patch`，仅当显式设置 `VINS_RUN_LOCAL_FEATURE_MIN_ANISOTROPY=0.01` 时才计算左目当前特征周围 11×11 Sobel structure tensor，并按 min/max eigenvalue ratio 丢弃低于阈值的点。补丁基于 #206 的 #0007 run-local 源码，未加入 `dependencies/sources.json`，不影响默认构建。
- #207 在独立 VINS build/install 和自维护 overlay 中编译运行；保持 `/clock`/PX4 HRT direct-current 路径、定位质量门、PX4 freshness 与控制发布者不变。保存首次带 residual 的 telemetry、对应双目图像、在线 overlays、离线 BGR 标注与 ULog。
- 修正继承的 ULog 分析脚本，使解释从本轮 action 与状态转换动态生成；#207 实际没有记录到 DESCEND/failsafe 状态。

## 结果

- #0008 dry-run 与 apply 通过；VINS `camera_models`/`vins` 构建 2/2，自维护运行时 overlay 构建 6/6。VINS binary SHA-256 为 `41dbec8e…67cad1`。前 30 条 filter 日志中有 29 条记录每帧候选点从 180 减到 152；优化器初始化后有 36 条 long tracks。
- 零位移、零 yaw 偏移诊断目标通过前置门并完成 3 秒停留。随后定位质量在仿真时间 29.624 s 以 `normalized_cost_exceeded` 锁定，normalized cost 为 1.208381，高于未变更的 1.0。该状态发生在 landing 序列中；目标本身不是导航验收。
- 756 个视觉 residual blocks 全部匹配到保存图像；Huber 代价复算误差 `5.12e-13`。保留观测的 11×11 tensor ratio 中位数 0.78360，P10/P90 为 0.67539/0.85534，0/756 低于 0.01。视觉 Huber cost 为 500.911，但完整 normalized cost 仍越线；本样本没有足够 cost-group 分解来归因剩余代价。继承的强边缘拟合统计与该轮图像场景不匹配，不作为边缘相关证据。
- ULog 时长 28.324 s、0 dropout；EV position/yaw/velocity 各 24/38 样本融合，所有 GNSS aiding flags 为零。PX4 进入 AUTO_LAND、触地并解除武装；未记录 failsafe。真值输入、debug_truth bridge subscription 与 observer 控制发布均为零。

## 验证

- `patch --dry-run -p1` 与补丁应用结果、源码基线/修改后 SHA 和 VINS binary SHA 已进入 run manifest。
- `python3 artifacts/runs/p5-px4-vio-ego-no-motion-direct-20261020-207/analyze_all_feature_residuals.py`：756/756 observations匹配，Huber代价复算通过。
- `python3 artifacts/runs/p5-px4-vio-ego-no-motion-direct-20261020-207/annotate_quality_crossing_images.py`：21 张离线 BGR 标注，逐图 36 项观测，不影响运行。
- `python3 artifacts/runs/p5-px4-vio-ego-no-motion-direct-20261020-207/analyze_px4_ulog.py`：EV/GNSS、着陆与 failsafe 状态重算完成。

## 局限与下一步

过滤器消除了捕获 residual 集中 ratio <0.01 的点，但没有让完整质量门通过；本轮只有零偏移目标。补丁保留为实验，不能进入 canonical VINS。随后对 0.30 m 横移/30° yaw 目标做两轮 run-local 复测，见 #008；P5 仍未通过。
