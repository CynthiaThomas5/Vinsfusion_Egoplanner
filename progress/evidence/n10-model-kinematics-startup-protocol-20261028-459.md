# N10.3/#459 无飞行运动观察器启动诊断

## 假设与唯一变量

假设：#458 的瞬时运动账本为空，是因为 PX4 根模型使用 `PX4_GZ_MODELS` 直接文件路径，而该变量未指向带 observer 插件的 run-local 根模型。唯一主要变量是 `D435I_N10_KINEMATICS=1` 时 PX4 根模型来源改为本轮已生成的 observer overlay；碰撞几何、场景、飞行参数、地图/规划配置不变。

## 运行方式与安全边界

以新的 run id 启动 SITL，`D435I_N08_MODE=hold`、`D435I_N09_CONTACTS=1`、`D435I_N10_KINEMATICS=1`，不运行 `mission`、不发送目标、不解锁。由 Gazebo Transport 只读订阅 `/debug_truth/model_kinematics` 并记录短窗口；另保存 `gz topic -i`、PX4 根 SDF 解析路径/SHA，以及同 ROS domain 的 bridge/PX4 状态读回。满足 bridge DISABLED、PX4 disarmed/landed、control topics 零样本后运行 `project.sh stop`。

## 判据

- PX4 模型来源报告指向 run-local `n09-contact-models/x500_d435i/model.sdf`，文件 SHA 与本轮 overlay manifest 一致，且模型根包含唯一 kinematics plugin。
- Gazebo 话题有发布者并在短采集中收到样本；元数据符合 `uav-model-kinematics/v1`，机体模型身份有效，状态有限，仿真源戳严格递增。采集仅验证 plugin 被实际加载，不将短诊断当作完整飞行区间覆盖。
- 无 mission/goal/enable/arm 控制行为；结束前确认 bridge/PX4 保持安全未武装状态。

缺字段、无发布或收不到样本均记录为诊断不足，不新增飞行拒绝门。若假设成立，下一次 N10 综合运行必须重做物理步 ledger；#458 仍保持原始失败/不足状态。
