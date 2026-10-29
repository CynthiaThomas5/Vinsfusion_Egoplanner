# N08 #319：中性俯仰分段下降剖面

## 假设与单一变量

#312 已完成 z=1 m 的后向观察与回正，但在连续下降约 5.1 秒后跨过原有定位代价门；#318 改变相机俯仰后，在下降前就锁定。#319 保留 #312 的前 14 阶段和中性俯仰，将 1→0 m 下降分成十个 0.1 m 小步，并在每个小步后静止 2 秒。

每个移动阶段按 #312 原先 1→0.5 m 的 12 秒和 0.5→0 m 的 7 秒比例计算，故测试变量是小步间的驻留，而不是另选速度。健康、时间、地图、空间、速度和跟踪门限均不改。

## 静态验证

- 35 个阶段，合计 482 仿真秒；profile wall 上限 750 秒。
- 前 14 阶段与 #312 已完成的同名基线剖面逐项相同；俯仰和最终航向维持零。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_preflight_scan`：50 项通过。
- `python3 tools/project_status.py`：Structure/design PASS；不代表构建或 SITL。
- `bash -n tools/run_n05_preflight_layout.sh`、`git diff --check`：通过。

## 运行结果

冷启动运行 `n08-cancel-highspeed-prescan-20261026-319` 在第 12/35 阶段中止：从 yaw=−π 回转至 yaw=−π/2 时，fresh 同 epoch 定位以 `normalized_cost_exceeded` 锁定，代价 1.007907，接收龄 0.000056 s、源龄 0.044 s。最后已记录的有效 trace 代价为 0.998161。仿真时钟当时仍正常前进；失败来自原有定位门，而非 Gazebo 时钟停滞。

本轮尚未回正，也未开始分段下降。因此新增驻留假设未得到测试结果；不能据此判断小步下降有效或无效。初始 N05 online/offline 一致拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`，没有释放后准入、mission preflight、live geometry、goal、control enable 或飞行。

扫描器确认夹具脱离、移除且落地。独立六秒 PX4／bridge 读回显示 DISABLED、未解锁、landed、控制模式／轨迹设定点／车辆命令样本均为零；只停止 #319 容器，退出码 0。详细结果：[运行报告](n08-segmented-neutral-descent-yaw-lockout-20261026-319.md)与[机器报告](n08-segmented-neutral-descent-yaw-lockout-20261026-319.json)。

下一项先对齐 #312 和 #319 在同一前置 yaw 返回阶段的 VINS 观测、残差、特征数、偏置、源龄与归一化健康代价。两轮共同前缀完全相同，却只有 #319 在回转阶段锁定；先从现有原始数据判断两次起始状态差异，再决定是否有值得做的新动作。不得重复 #319 或改门限；若数据无法区分原因，保留未通过状态并报告实际阻塞。
