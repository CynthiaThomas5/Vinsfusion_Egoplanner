# GOAL C 视角变化后重新观测 guard 样本 #333–#337

## 结果

针对 #332 中 `t=1.08 s` 的 EGO full-spline guard 拒绝点，本轮用相机光学坐标中的同一光线向量进行 run-local 姿态变化试验。#337 在传感器 fixture 上使用相等实际时长的加速与刹车，并在仿真时刻 34 s 取后快照。目标从原始视场外的像素 `(635.1,-350.6)` 移到 `(490.2,51.0)`；同一个 10 cm voxel `[122,118,5]` 在同 epoch、同 `map_id` 下从 unknown 变成 raw free，inflation mask 为0。两份快照深度源龄分别109 ms和113 ms；已知体素从8,034增至25,401，其中17,006个 unknown→free、361个 unknown→occupied。NPZ 独立回读与计数复算的12项检查全部通过。

## 过程与边界

- #333 在未增加上墙视觉纹理时施加较大抬头，VINS 报告 `stereo_features_insufficient`，mapping gate 关闭并重置 `map_id`。遵守身份隔离规则，没有把 reset 前后地图拼接。
- #334 基线已抓取，但 run-local observer 在访问错误字段时抛出 `KeyError`，没有后快照，按 harness failure 排除。
- #335 用17°左右姿态变化观察一个较浅代表点，同身份下 unknown→free；#336 用 #332 的原始光线向量复现了同一变化，但 IMU 显示刹车后又转动约13°，因此 #337 修正了相位持续时间并提前取样。
- #337 的 VINS 估计相机相对转角约31.8°，IMU 脉冲积分约−32.2°，从释放到快照的额外积分约0.5°；运行期间观测到的 EGO `odom or depth lost!` 日志为0。EGO 处于无目标状态，未发布轨迹；图中无真值与控制 topic、PX4 bridge、controller 或 traj_server。
- 纹理标记和力矩驱动只存在于 `artifacts/runs/` 的调试世界与脚本。没有改动 `src/own`、`src/vendor`、依赖补丁、PX4 参数或中央建图配置。unknown 策略保持 fail-closed。

## 验证

`python3 -m py_compile` 检查本轮 run-local Python 工具；`bash -n` 检查容器与仿真 runner。`analyze_snapshot_pair.py` 对 #335、#336、#337 的快照身份、网格、occupancy、视锥投影、新鲜度、归档 SHA、地图增量和运行图执行独立检查，三轮均通过。最终还运行 `python3 tools/project_status.py` 与 `git diff --check`；这只验证项目结构/文档一致性，不提升本轮证据为导航验收。

轻量报告见 [证据汇总](../evidence/p2-camera-pitch-guard-sample-20261021-337.json)，每轮 run manifest、脚本、原始快照、运行日志和哈希位于对应 `artifacts/runs/p2-camera-pitch-*-20261021-33[3-7]/`。对话摘要：[2026-10-21-008](../../collaboration/dialogues/2026-10-21-008-camera-pitch-guard-sample.md)。

## 下一步

保持 GOAL C pending。下一步评估受碰撞约束的机体视角动作、机体扫掠净空与多布局地图几何；单独的传感器 fixture 转动不证明真实飞行器可以安全地做这项动作，也不证明其他 unknown 可以清为 free。
