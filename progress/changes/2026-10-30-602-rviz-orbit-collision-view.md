# #602 恢复RViz三维碰撞地图斜视角

- 用户要求恢复为无人机主视角的碰撞地图显示；[对话摘要](../../collaboration/dialogues/2026-10-30-602-rviz-orbit-collision-view.md)。
- 将`config/rviz/mapping.rviz`从TopDownOrtho恢复到原Orbit视角参数。保留observed obstacle history与inflated occupancy map，不改显示颜色、背景或建图/碰撞逻辑。
- 当前run的mapping.rviz重新从源preset生成；只重启RViz viewer以加载，Gazebo、ROS节点及地图发布器继续运行。截图确认斜视三维地图、历史占据与碰撞层可见。
- 验证：源/运行时YAML解析和层启用状态PASS；`python3 tools/project_status.py` PASS；`git diff --check` PASS。未改运行代码，无构建/飞行测试。
- 证据：[截图与哈希](../evidence/rviz-orbit-20261030-602.md)。当前GUI保留。
