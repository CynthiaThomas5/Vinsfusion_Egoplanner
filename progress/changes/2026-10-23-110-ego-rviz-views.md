# #110 接入只读 EGO/RViz 导航视图

目标：完成用户明确指定的 GUI 显示接入；不是 N06 Goal 运行或下一主线子项。停止原因为本轮功能和限定验证完成。

## 实际改动

- `uav_navigation` 新增可选 `navigation_visualization` 及纯几何模块：真实 de Boor B 样条采样、有界 VINS 历史、已接受目标／yaw、共享配置包络和定位／地图源龄／规划状态。
- 输出只含 `/visualization/ego/*` Path／Marker（另有 ROS 标准 rosout／parameter_events）。按 epoch、会话坐标、目标及取消身份过滤；定位失效、地图身份切换、取消和时间倒退清除失效内容。时间倒退锁存，等待新会话。
- 上游 Marker 的 `world` 标签仅在绘图副本中改为其输入所在会话 odom；原始算法消息、TF、控制数据不改。调试图层按消费者订阅，默认不触发上游额外绘图。
- `config/components/navigation/visualization.json` 保存采样和历史限值；半径继续读取唯一 envelope 配置。RViz 新增默认导航层和默认关闭的调试组，保留地图及相机图像。
- launch 增加默认关闭的 `enable_visualization`；`sim_runtime.sh` 仅 GUI 启用。更新运行说明和包依赖，添加几何单测与合成 ROS 探针。

## 验证与证据

构建 2 包、13 项单测、合成 ROS 五组检查及实际 RViz/Xvfb 加载均通过，命令／限定与哈希见 [验收记录](../evidence/ego-rviz-views-20261023-110.md) 和 [JSON](../evidence/ego-rviz-views-20261023-110.json)。

首次 ROS 检查发现 Jazzy JumpThreshold 必须显式提供 min_forward，已修正后重跑通过。一次 py_compile 因 Docker 写入的工具 __pycache__ 权限失败，改用不写字节码的 compile(source) 完整语法检查通过；未调整其他用户文件权限。最终执行 `python3 tools/project_status.py`、`git diff --check` 与 `git status --short --branch`，结构通过仅表明一致性，不作为飞行证据。

## 局限与交接

本轮未启动飞行或 Gazebo/PX4，不重启另一个 N06 会话。新建 GUI 会话自动使用新视图；当前会话不自动更新。目标 GPU 的实际场景观感／负载待后续正常运行观察；显示包络不构成准入证书，A* 层仅在上游实际发布时出现。

工作树原有 GOAL、N06 配置／工具／记录等修改属于既有工作，未回滚或计作本项实现。CURRENT 仅增加本项交付事实；milestones、N06 与 next_goal 不变。下一步仍按 CURRENT 的 N06.4 恢复条件推进，不因本项完成改为飞行。

[对话摘要](../../collaboration/dialogues/2026-10-23-110-ego-rviz-views.md)。未经要求未提交或推送。
