# uav_navigation

`task_state.py` 保持 ROS 无关的任务策略；`node.py` 将策略接到 `NavigateToPose` action、定位状态／里程计、EGO 目标和轨迹取消话题。动作要求目标 frame 为当前 `odom_<epoch>`，且定位、里程计新鲜、EGO 目标与取消订阅端均在线。定位失效、epoch 切换、ROS clock 回退、过期位姿、超时和显式取消会返回带原因的终态，并向 EGO 与轨迹服务器发送按 `goal_id + epoch` 匹配的清轨迹请求。到达需要位置与 yaw 同时在容差内持续满足 dwell 时间；替换目标时先取消旧目标再发新目标。

`launch/navigation_supervisor.launch.py` 启动动作节点，并从仓库的 `config/components/navigation/task_supervisor.json` 读取唯一话题配置；用 `project_root` launch 参数传入仓库根目录。EGO 的 `NavigationCommand`／`TrajectoryCancel` 接收端和 `traj_server` 的轨迹取消／yaw 采样已实现。导航节点使用 ROS clock jump callback 检测任意负向时间跳变，避免为 `/clock` 每条消息创建第二个用户回调；接收仿真时间仍由 rclpy `use_sim_time` TimeSource 提供。内部 shutdown 会将活动 action 标记为 ABORTED、发布对应轨迹 ABORT，并在销毁 node/context 前等待 action callback 完成及 result service 投递。合成测试覆盖一纳秒回退、冻结 `/clock` 时的墙上时间 freshness guard 和 shutdown ABORT。新增 `debug_truth_ego_px4.launch.py` 将 debug_truth 输入 remap 到建图适配器、EGO、导航和 PX4 bridge；#34 实测完成同一 epoch 的 EGO action、READY轨迹、PX4 到达和降落。P3 debug_truth 阶段已通过；最终视觉和避障净空仍未验收，详见 `progress/evidence/p3-px4-ego-flight.json`。

任务核心单测：`python3 tools/test_navigation_task_state.py`。ROS 接口探针：`tools/test_navigation_adapter.py` 与 `tools/test_trajectory_server.py`；运行步骤和限制见 `progress/evidence/p4-navigation-ego-action-cancel.json`。PX4 setpoint 和 `OffboardControlMode` 只能由 `uav_px4_bridge` 发布。

#061离线审查发现当时目标入口缺少空间查询；#062已增加只读raw目标球准入。ROS action协议接受后，先绑定epoch／map_id／frame查询实际地图，全部相交格已知free且返回新鲜才向EGO转发。未知／占据／越界／超时等返回rejected；并发准入失败、等待时取消不影响既有轨迹，地图身份变化取消活动轨迹。0.5m球半径与0.4仿真秒源龄复用mapping canonical配置，查询等待0.25墙秒。终点球不是目标可达性／整条路径净空证书。旧4m复访配置已禁用。补齐当前epoch／map_id／融合新鲜度绑定的在线空间准入与完整轨迹验证前，不据此开启新的任意目标飞行。见[审查](../../../progress/evidence/goal-admission-20261022-061.md)。
