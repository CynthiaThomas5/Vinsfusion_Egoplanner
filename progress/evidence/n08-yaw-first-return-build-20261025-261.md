# N08.261 EGO 原地转向构建

**结果：构建与静态验证通过；没有飞行或 PX4 动作。**

用户要求返航不得倒飞：前向停车后，先让机头在当前位置转向约 180°，再让 EGO 按机头前向路线规划返航。#260 的失败记录只证明原航向返航目标被地图以 `map_query_unknown` 拒绝，未证明拒绝一定由相机后方盲区导致。

EGO 常规位置规划器会拒绝小于 0.2 m 的路径，所以原地仅改变 yaw 的目标原先无法生成轨迹。新增 0045 补丁让 EGO 对定点 yaw 目标发布 16 控制点、三次、位置恒定的 26 秒 B 样条；yaw 控制点沿最短角度方向平滑变化。180° 转向的 yaw 导数控制界为 `3π/(11×2) = 0.4284 rad/s`。轨迹仍需通过现有 EGO 完整曲线及终端保持 raw-map 证书；PX4 控制仍只由 `uav_px4_bridge` 发布。

返航试验执行器现在要求：转向球体已知无占据、定点转向轨迹和 yaw 终点合格、转向后收到更新的融合地图、整个返航胶囊已知 free、机体系前向速度不倒退。离线独立评估还会用 Gazebo 真值检查转向时的位置变化和返航速度相对机头的方向。所有 unknown、身份、源龄、定位与健康门限保持不变。

验证命令与结果：

- `bash tools/project.sh build ros`：17 个 ROS 包构建完成，`ego_planner` 编译成功；有既有 deprecated API 编译警告。
- `python3 tools/project_status.py`：PASS（仍只是结构检查）。
- `PYTHONPATH=. python3 -m unittest tools.test_n08_braking_evaluation`：9 项通过，包括机体系前向与倒向真值对照。
- `PYTHONPYCACHEPREFIX=/tmp/codex-pycache python3 -m py_compile tools/run_n08_braking_trial.py tools/debug_truth/evaluate_n08_braking.py tools/test_n08_braking_evaluation.py`：语法检查通过。
- 0045 补丁在临时上游路径重放后，EGO 源文件 SHA256 与依赖清单一致；`git diff --check` 通过。

编译产物与补丁／源码哈希见本目录的 JSON 报告。当前 EGO 二进制已变更并由 #261 构建指纹锁定；N08 执行器会在运行时核对该二进制与 run manifest 一致。

**限制与下一步：** 尚未证明 live EGO 会接受这条定点 yaw 样条，也未证明转向位置保持、前视地图更新或实际返航方向。下一子项 #262 使用全新运行与 fresh N05 准入重做制动、原地转向、前向返航和降落；不得复用 #260 地图。
