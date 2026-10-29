# N10.3 #365 动态障碍工具冻结与运行前身份

状态：**工具已冻结；SITL 尚未启动。** 本报告只证明本轮工具身份及静态检查，不代表服务已在线确认或飞行通过。

## 冻结身份

- #364 协议 SHA-256：`c003ed51246e9d423b5a40ccabb098f7e1d42db9ed53d50c00326670e05fcdd8`
- #361/#362 runtime contract：`fdf104f5bd7b733128656fc4736af001f9ecdcbe1d93de123b41c7974a511a2f`，665 项输入。
- 本轮 `n10-tool-freeze.json` 固定了 injector、driver、旧 N10 校准分析器和动态障碍离线分析器哈希。
- 预期 PX4 SITL run：`n10-20261027-365-live-obstacle-replan-current`。

## 工具行为

Injector 读取 `/navigation/ego_goal` 的目标时间戳和同 goal/epoch 的首条 EGO B 样条；在目标发出后 12 仿真秒仅调用一次 `/world/vio_initialization/create`，建立协议指定静态方箱。只读记录相机深度／彩色帧、EGO occupancy 点云局部统计、raw occupancy query、完整同 goal B 样条与 position command。观察器不发布 ROS topic、不订阅真值、不发布控制；只有协议规定的 1 仿真秒无替代轨迹时才通过 action cancel service 发出 caller-cancel。

离线分析会比较注入前后样条中心线与障碍盒距离，并记录同区间 raw occupancy／传感器观察。#361 中已见正常滚动规划反复发布新 `traj_id`（83 条样条记录），因此单独的 ID 变化不足以证明障碍导致改道；本轮不更改已冻结 #364 判据，但报告会保留这一解释限制。

## 保护门源码核对

- 定位质量／定位回执龄门已移除；`normalized_cost` 只记录，不作为本轮任务拒绝阈值；未发现 raw-free 整曲线拒绝进入当前 `official_ego` 运行链。
- 保留地图身份／新鲜度和 PX4 bridge 状态、控制约束及时间/epoch 完整性。它们不由本轮工具新加；工具不修改运行源码。

## 运行前验证

- `bash -n artifacts/n10-prepared/n10-20261027-365-live-obstacle-replan-current/n10-runtime-driver.sh`：通过。
- `python3 -m py_compile .../n10_live_obstacle_injector.py .../analyze_n10_dynamic_obstacle.py`：通过。
- `python3 tools/runtime_manifest.py /tmp/n10-365-runtime-current-final.json`：与 #361/#362 基线一致，SHA-256=`fdf104f5...a511a2f`。
- SITL 启动后、飞行前，driver 还会要求实际 Gazebo create service、ROS action cancel service、raw map query service 和 contact observer 就绪。运行结果尚未产生。

机器可读身份与哈希：[n10-tool-freeze.json](../../artifacts/n10-prepared/n10-20261027-365-live-obstacle-replan-current/n10-tool-freeze.json)、[JSON](n10-live-obstacle-runtime-prelaunch-20261027-365.json)。
