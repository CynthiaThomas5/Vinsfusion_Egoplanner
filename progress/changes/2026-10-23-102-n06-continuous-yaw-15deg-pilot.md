# 2026-10-23 #102 N06 continuous 15° yaw pilot

对话摘要：[N06 continuous 15° yaw pilot](../../collaboration/dialogues/2026-10-23-102-n06-continuous-yaw-15deg.md)

## 结果与记录

- r27 沿用 r26 wall 与纹理 surround、连续加速／匀速／减速、四分之一角加速度，名义转角 15°；fixture truth 实测 14.731°。
- `normalized_cost_exceeded` gate 在 sim 62.404 s 关闭，VINS `n_pts=2`、估计 yaw 10.161°；在线锁存 normalized cost 1.34155，超过未改动上限1.0。首条 invalid LocalizationStatus 在 sim 62.478 s／truth yaw约9.854°；MapStatus于sim62.569s换map_id并关闭为`map_reset_acknowledged`。
- 150秒输入记录落盘：1,762 depth/camera-pose pairs、881 optimized odometry；健康 reset 后 MapStatus 未恢复，snapshot readiness 在120秒后超时，无snapshot／live EGO。runner exit1，确认容器和项目进程停止。
- 新增 [机器报告](../evidence/n06-continuous-yaw-15deg-observation-20261023-102.json) 与 [证据报告](../evidence/n06-continuous-yaw-15deg-observation-20261023-102.md)。N06/S4和`next_goal=N06`保持未完成。

## 下一子项

以 r27 为对照，运行 r28 单轴 X 后退2.4m并回到原点，保持 wall 布局及同一 textured surround；profile为既有`n06_x_visibility_slow.json`（SHA-256 `653733f873234da35fb38af4f80771707190bd21df595372c88fa2924234988f`），无yaw／Y／Z。假设后退视角可将原点body球从相机前方成像，并通过平移视差避免r27的yaw健康失效。之前r14／r16使用同profile但无surround，均在`input_features_insufficient`时锁存；r28据此保持新纹理场景。记录在 [CURRENT](../CURRENT.md)、[N06总报告](../evidence/n06-full-curve-layout-review-20261023.md) 与机器摘要。

运行命令：

```bash
bash tools/run_n04_map_layout.sh n06-20261023-wall-r28 wall_box_column 91 motion_n06 config/components/simulation/n06_x_visibility_slow.json
```

## 限制

本轮仅 sensor-only Gazebo/VINS/EGO mapping diagnostic；未启用PX4、bridge、controller、setpoint或flight。未放宽unknown、N05包络／误差预算或N06验收。r27健康锁存后没有地图／曲线证据，因此不把约9.85°视作合格入口。
