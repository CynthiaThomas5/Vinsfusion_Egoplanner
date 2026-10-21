# P5 无目标悬停与 VINS 时间／代价复测 #181

## 任务摘要

- 接续 #180 的 Ceres 分组代价诊断，为其补一个同配置、无导航目标的 D435i SITL 悬停对照，并记录图像配对队列龄、特征跟踪和代价评估耗时。
- 遵循项目边界：不改变 canonical 第三方源码、不降低质量门；只读 Gazebo 真值只供独立 evaluator，PX4 控制设定点仍由 `uav_px4_bridge` 独占。

## 决定

- 通过 bridge 的 enable/disable 服务请求起飞、保持与落地，不调用导航 action。将计时插桩只打入 #181 run-local VINS 副本，避免增加完整分辨率图像 observer 或修改 vendor 主树。
- 保留一次性 Ceres 分组代价计算，评估发生于该 VINS 进程首次 `normalized_cost >= 1.0` 时。

## 结果

- #181 无 goal 悬停20.011秒，dwell 内代价最大0.544；固定单次 SE(3) 对齐的 hold 子集位置误差 P95 1.23 cm。411组双目时间戳 skew 为0，前端时间 P95 9.06 ms。
- dwell 结束后进入降落；约2.51秒墙钟后 normalized cost=1.0164，Ceres 分组评估耗时0.189506 ms。PX4 最终落地、解除武装且 failsafe=false；质量门未放宽。
- 首次越线组分布为视觉61.65%、边缘化38.08%、IMU0.28%。单轮降落阶段越线不能识别 #180 目标运动越线的根因；#181 仅为诊断，不是 P5 或 GOAL 验收。

## 待办

- 复跑 no-goal 悬停基线检查可重复性，再继续横移／偏航、障碍净空、地图快照、故障注入和长时验收。
- 维持 truth observer 隔离、唯一 PX4 控制发布者与 fail-closed 质量门；GOAL A–H 仍未完成。
