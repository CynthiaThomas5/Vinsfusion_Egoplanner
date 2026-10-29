# N10.3 #367：EGO 官方重试行为下的动态障碍复测协议

状态：**协议和工具已冻结；SITL 尚未启动。** 本轮只验证单 D435i、Gazebo/PX4 SITL 的诊断行为，不构成 N11–N16 正式次数或 N10 通过。

## 假设与唯一变量

#365 在目标后 12.016 仿真秒收到 Gazebo 方箱创建 ACK，注入时真值位置约为 `[-3.275, 1.440, 0.909] m`，距箱体中心约 3.61 m（水平 3.58 m；沿 X 偏移 3.27 m）。EGO occupancy surface 点云后来在箱体附近出现；同一目标先后生成 traj_id 45–72，其中45仍穿过箱体，之后轨迹中心线开始绕开。但约注入后5.47秒，EGO 原生优化器再次报告 refined trajectory collision，`reboundReplan` 失败；项目补丁0039将该次暂时不可行直接变成 `planner_full_curve_planning_failed` 并中止目标。

本轮相对#365仅变更 EGO 补丁0053：移除项目自加的整条曲线raw occupancy／地图就绪准入调用，恢复上游在规划暂不可行时的重试状态转移。地图膨胀占据层碰撞判定、EGO自身轨迹碰撞回调、深度超时／紧急停车、PX4唯一控制桥均保留。目标、起点、速度参数、箱体、注入时刻和观察器不变。该试验验证“继续重试能否恢复”，不预设成功。

## 冻结身份

- runtime contract SHA-256：`15d935eb803e76eb378aa4aa566d2d7b46b97168e2c75e7e0ee5d87878ed57a6`（665项）
- protocol SHA-256：`5a814b84b2b26a126b2b4dffba651e9123df4b4670754d634d70349f09fb7620`
- injector SHA-256：`0647cc9f0dba53b8ca5d98a8e3bb7a595ff6df28ad5e559c52ecf4fa14f04cb8`
- driver SHA-256：`26a69a8f6b4295ffb2d27f776b406f2b9da57a79e64510c0f822167e55b6bf63`
- dynamic analyzer SHA-256：`686e410c49472dc6b5cf66490a776dd879a2bd0a9718eddedd4419ccc74d3453`
- box-clearance analyzer SHA-256：`8b2b74b8dc3473ccde413e9d6d85f244600e9d3855fa6644e7a2f7abec946aaf`
- EGO binary SHA-256：`25179a8ccdec7489c463f02e662180327bd34f90ef293ab1d0a0a85593d4982b`

协议输入、observer与离线报告均不发布目标／地图／控制；唯一世界改动是按协议创建一个静态方箱。真值只进入离线评估。

## 运行前验证

- ROS构建：`bash tools/project.sh build ros`，17包成功；日志见`artifacts/runs/n10-20261027-366-ego-patch-build/build.log`。
- `bash -n` driver与三个 run-local Python工具 `py_compile` 通过。
- 项目 runtime manifest 在 SITL 前复算仍为上述 SHA；运行器飞行前还需检查 Gazebo create、action cancel、地图查询、接触观察器和真实 launch 参数。
- 预期 run：`n10-20261027-367-ego-retry-live-obstacle`。

该报告仅冻结复测输入，不代表在线服务已确认或飞行结果已通过。
