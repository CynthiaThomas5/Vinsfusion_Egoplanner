# P5 全量 visual residual 与边缘各向异性诊断（#206）

对话摘要：[2026-10-20-006](../../collaboration/dialogues/2026-10-20-006-p5-full-feature-edge-correlation.md)。轻量证据：[全量 residual/边缘报告](../evidence/p5-vins-all-feature-edge-correlation-20261020-206.json)。

## 变更

- 新增 `dependencies/patches/vins/0007-all-feature-residual-observations.patch`。在 #0006 run-local 诊断源码后，只扩大首次 normalized-cost crossing 的 observation JSON 列表；不会更改 residual、Ceres solve、feature tracking、健康状态、控制或 threshold。该补丁未加入 `dependencies/sources.json`。
- 新建 #206 源码副本，检查 #203 #0006 estimator SHA，执行 #0007 dry-run/apply，并在 Jazzy 新 build/install 编译；run-local manifest记录源/补丁哈希与顺序。
- 保存所有目标双目帧与 798 residual overlays；离线生成22幅 BGR annotation/crop，另用逐帧图像边缘和 Sobel structure tensor 对完整 observation 做关联。

## 结果

- #0007 源码干跑和应用通过，`camera_models`/`vins` 构建2/2；运行时 bridge overlay 6/6。VINS 二进制 SHA 与 #203不同，且与 #0007 patched source manifest 对应。
- #206 goal 已派发，首次 normalized_cost=1.0780147，既有门限中止动作并触发降落，最终 landed/disarmed。P5 不通过。
- 首次越线包含798个二维视觉 residual blocks/42 tracks；全部 target image timestamps 匹配，observer 未见 missing image。再次计算 Huber residual 成本和 VINS grouped visual cost的误差为4.55e−13。
- norm>1.5 的38个 blocks来自6个feature IDs，全部距逐帧高梯度线≤0.289 px，38/38残差沿线切向主导；累计Huber cost891.526，占视觉组98.502%。高残差处11×11 Sobel tensor min/max eigenvalue ratio中位数0.00256，低残差组0.78359。该关联强但仍是单一场景内的图像/优化观测证据，不证明唯一根因。
- PX4 ULog仿真时长28.216秒，无dropout；EV position/yaw/velocity各22/40样本融合，GNSS aiding全零、电池flags零；触地后短暂DESCEND/failsafe，后续解除武装。

## 验证

- `patch --dry-run -p1` 对 #203 保存的 #0006 estimator 源码成功；应用后 estimator SHA 与 #206 manifest一致。
- #206 独立 Jazzy VINS构建2/2，SITL自维护 overlay构建6/6；包前缀、epoch、无真值、无控制 observer发布证据已保存。
- `python3 artifacts/runs/p5-px4-vio-ego-no-motion-direct-20261020-206/analyze_all_feature_residuals.py`：798/798 observation匹配目标帧；Huber cost重算与组cost差4.55e−13。
- `python3 artifacts/runs/p5-px4-vio-ego-no-motion-direct-20261020-206/analyze_px4_ulog.py`：EV/GNSS、dropout、电池与 landing/failsafe timeline生成完成。
- 运行只构成 SITL 诊断，未做 replay、实机或 P5 通过验证。

## 局限与下一步

所有高代价观测位于低各向异性强边缘，但仍可能由追踪、标定、运动或场景共同造成。下一步仅在 run-local feature tracker中加入明确 opt-in anisotropy filter，比较 feature数量、cost与 action 结果；不可改当前质量门或把单次成功称为 P5 通过。
