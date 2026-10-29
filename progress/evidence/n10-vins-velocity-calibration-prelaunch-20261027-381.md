# N10.3/#381 运行前身份检查

**状态：**SITL 尚未启动；本文件只冻结运行身份，不是飞行证据。

- Runtime-contract：`547082a4538a871dd3c3b9b26c0f6b45369fa18bf1b73a8d93f219ef3e537cce`，文件数 666。
- planner：`config/components/mapping/n10_horizon5_speed080_calibration.json`；max_vel=0.8、max_acc=0.25、horizon=5.0、official_ego。
- spawn：`config/components/simulation/n10_long_range_spawn_minus8.json`，SHA256 `b2534428e59c4b953e49f08a759b5cda8f1f0ea40f3a7d764923a797ff6f4aa2`，位姿 `(-8, 0, 0.3, 0, 0, 0)`。
- 目标：原 N10 16 m 位置+yaw 单目标和600仿真秒 ACTIVE hold；动态箱体及静态 cylinder 观察与 #376 相同。
- 唯一变量：只读 recorder 增加 raw VINS `twist.linear` 速度字段，并离线和独立 Gazebo 真值比较。无控制、飞控、planner、世界、速度、碰撞策略或门限改动。
- Protocol SHA256：`053e4924c424501af851f32ae136c7cc15de54aab9cfbaf85ae7cbb431cd7ae1`。
- recorder SHA256：`eb39df81bd03241e146f12361d0a2113776fd004e934d37c0cce9633e95ac587`；velocity evaluator SHA256：`4a6a3d5c44fbd60a115a46c1657feba69ab2f638d9a44ad11470ddc8b8e6ec1c`。
- Run-local driver 与注入器哈希由 freeze 清单绑定。启动前 driver 会再次核验 runtime、协议、planner/spawn 和图连接。
- 运行后需完成观测器 terminal coverage 和速度样本完整性检查；任何量测缺失只判该指标不可判，不补零。停止容器前需独立读回 LANDED/disarmed/control-disabled/zero-control。
