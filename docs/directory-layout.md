# 文件与目录职责

| 位置 | 保存内容 | 边界 |
| --- | --- | --- |
| src/own/uav_interfaces | 统一 msg／srv／action | 仅维护实际接口，不预建未来消息 |
| src/own/uav_sim | Gazebo→ROS 数据桥与帧规范化 | SDF 原件在 simulation，不重写采样 stamp |
| src/own/uav_localization | VINS 输出适配、body→base_link、健康与 epoch | 不把稀疏特征点当导航地图 |
| src/own/uav_mapping | 深度／位姿校验、关键帧及地图生命周期适配 | 复用 vendor 的 plan_env 占据实现 |
| src/own/uav_navigation | 目标、yaw、取消、到达、超时及失败协调 | EGO／航点指令均先交唯一控制出口 |
| src/own/uav_px4_bridge | 外部里程计、坐标转换、EKF 状态、Offboard 出口 | 规划坐标与飞控原点对齐，独占控制发布 |
| src/own/uav_bringup | 预留职责说明（无ROS包） | 当前编排在各包launch与tools/project.sh；不重复造包 |
| src/vendor | VINS、EGO、px4_msgs、Agent 等 ROS 依赖 | 只导入版本清单选中的包，不复制多套算法 |
| simulation/models | D435i 等效模型、机体安装 | K、基线、外参和 IMU pose 的几何来源 |
| simulation/worlds | 当前ego房间及受控评估场景SDF | 世界几何只供仿真和离线评估 |
| simulation/airframes | 机架生成约定 | 参数在config，tools/stage_px4_debug_params.py生成各轮机架 |
| config/profiles | debug_truth、vio_mapping、vio_closed_loop | 声明生命周期与输入边界；不等同最终验收通过 |
| config/components | VINS、地图、PX4、导航参数 | 由包launch和运行入口引用；共享参数只保留一个来源 |
| config/local | 本机路径 | paths.example.json 可跟踪，实际 paths.json 忽略 |
| dependencies | 上游清单、来源快照、patch | checkout 本体不进入本项目 Git |
| docker | 固定镜像约束与构建说明 | 公共底图构建链未补全；交付固定镜像归档 |
| tools | 统一工程入口、回归、观测和评估 | 真值只在debug_truth离线评价 |
| collaboration/dialogues | 脱敏任务讨论摘要 | 与代码进度分离，不宣称实验通过 |
| progress | 当前状态、阶段、改动记录、轻量验收证据 | 不保存原始聊天和大数据 |
| artifacts/runs/<run_id> | 每次运行的日志、bag、地图、截图、指标 | ignored；run_id 与 epoch 分别记录 |
| external | PX4-Autopilot 等非 ROS checkout | 允许本机路径引用，不复制旧仓库全部历史 |

当前有6个可构建自维护ROS包，统一构建至build/和install/；uav_bringup仅保留职责说明。目录结构检查不替代编译和SITL结果。
