# #601 设置RViz俯视全局视角

- 用户要求在RViz从高处向下查看。对话摘要见[601对话](../../collaboration/dialogues/2026-10-30-601-rviz-topdown-view.md)。
- `config/rviz/mapping.rviz` 默认view改为 `TopDownOrtho`，视野25m，中心(odom x=8,y=0)，适配pillars起点(-8,0)与16m路线。仅视角改变，沿用现有背景、历史地图和碰撞层。
- 活动run `gui-20261030-154042-3829973`的mapping.rviz同步更新，并重启RViz viewer进程；Gazebo/飞控/导航容器和地图发布器保持运行。截图确认俯视正交全局地图与任务轨迹。
- 验证：`yaml.safe_load`解析源码和运行时配置PASS；`python3 tools/project_status.py` PASS；`git diff --check` PASS。
- 证据：[截图及哈希](../evidence/rviz-topdown-20261030-601.md)。无构建或飞行测试（此改动仅为RViz view配置）。
