# N10.3/#381 raw VINS velocity 量测协议

## 目的

#376 的 current-runtime 长航段记录含位置与姿态，但只读观测器没有保存 raw VINS `nav_msgs/Odometry.twist.twist.linear`。因此无法从现有归档复算原始 VINS 速度误差。此次只扩展观测字段并增加离线复算器，确认速度字段的实际语义，并在同一 16 m 目标、动态箱体和 600 仿真秒 ACTIVE 保持上测量速度误差。

## 唯一变量与固定条件

- 唯一变量：只读 recorder 新增 raw VINS world-frame 线速度采样；新增离线 evaluator 将该值与 Gazebo 真值作比较。
- 固定：single D435i、PX4 SITL、`official_ego`、`max_vel=0.8`、`max_acc=0.25`、horizon 5 m、`x=-8 m` spawn、原 16 m / +0.1 m / +0.2 rad 单目标、目标后 600 仿真秒 ACTIVE hold、12 仿真秒后插入同一 0.8 m 箱体、静态 cylinder 观察、碰撞模型与项目已移除 health gate 的状态。
- 不增加/改变速度限制、健康门、到达值、地图策略、控制发布者或安全阈值。观测器只订阅，不发布控制。

## 速度测量定义

- VINS 上游 `src/vendor/vins_fusion/vins/src/utility/visualization.cpp` 将 `estimator.Vs` 写入 raw odometry `twist.linear`；该量以 VINS `WORLD_FRAME_ID` 表达。recorder 原样保存。
- 真值速度以 `d435i_link`（D435i IMU 原点）为参考，沿用 N01 full-state evaluator 的中心有限差分方法：在每个 raw source stamp 两侧各 0.1 仿真秒取真值，求 0.2 仿真秒对称窗口平均速度；真值插值括距最多 0.04 仿真秒，不外推、不修时间戳。
- 用 `evaluate_odometry.py` 在 PRESTREAM 前的单次 scale=1 刚体对齐旋转将 VINS velocity 转到真值 world；不拟合路径、不分段重对齐。
- 分别统计 goal source stamp 至 action completion source stamp、之后 ACTIVE hold 至 LANDED、全程 PRESTREAM 至 LANDED 的速度误差 RMSE/P50/P95/max 和 xyz 分量；同时报告样本覆盖、source 间隔、真值最大间隔。误差统计仅为诊断，不预置验收阈值。

## 预期采集与终止条件

目标必须在预检通过后只提交一次。flight runner 结束后观测器覆盖 terminal record；依序保存 truth、raw VINS velocity、planner、bridge、contact 和 source timeline；离线产出定位、速度、到达、动态重规划、净空与接触报告。无论实验成功或失败，先独立读回 LANDED/disarmed/control-disabled/zero-control，再停项目容器。数据缺失则将速度项标记不可判定，不能以零值补齐。

## 冻结身份

- run：`n10-20261027-381-vins-velocity-full-route`
- runtime：`547082a4538a871dd3c3b9b26c0f6b45369fa18bf1b73a8d93f219ef3e537cce`（666 个文件）
- protocol SHA256：`053e4924c424501af851f32ae136c7cc15de54aab9cfbaf85ae7cbb431cd7ae1`
- recorder SHA256：`eb39df81bd03241e146f12361d0a2113776fd004e934d37c0cce9633e95ac587`
- velocity evaluator SHA256：`4a6a3d5c44fbd60a115a46c1657feba69ab2f638d9a44ad11470ddc8b8e6ec1c`
- upstream VINS velocity source SHA256：`ae4f21db23c3359f3b173ea7577c50327ec8b2e0f68e76e9558ca0252e978bd7`
- 完整运行前身份：[prelaunch report](n10-vins-velocity-calibration-prelaunch-20261027-381.json)。

本协议只定义 N10.3 诊断量测，不是 N10/N11–N16 资格或速度安全保证。
