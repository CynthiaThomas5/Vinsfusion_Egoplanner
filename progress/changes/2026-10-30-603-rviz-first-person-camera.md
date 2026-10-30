# #603 RViz 第一视角相机

对话摘要：[2026-10-30-603-rviz-first-person-camera.md](../../collaboration/dialogues/2026-10-30-603-rviz-first-person-camera.md)

## 过程与结论

- 试验曾成功构建可视化 TF、显示相机图像并完成柱群 16m 任务；详细结果见[证据](../evidence/rviz-first-person-20261030-603.md)。
- 用户随后要求恢复最开始的 RViz 视图并停止继续。已移除 Camera display、恢复 Orbit preset、撤销 localization TF 代码和依赖；已完成 16m 的日志、截图保留作审计，不据此更新里程碑。
- 回退后重建命令 `docker exec d435i-gui-20261030-162149-3867210 bash -lc 'cd /workspace; source /opt/ros/jazzy/setup.bash; colcon build --base-paths src/own --packages-up-to uav_localization'` 通过，3 个包完成。
- 已从仓库配置重新生成当前会话 RViz 配置并重载窗口；运行配置和仓库配置均使用 `rviz_default_plugins/Orbit`，没有 Camera display，D435i RGB/left 图像显示及此前已有的障碍历史层、0.15m 占据格设置保留。恢复后的窗口截图：[rviz-orbit-restored.png](../../artifacts/runs/gui-20261030-162149-3867210/rviz-orbit-restored.png)。
- `git diff --check` 通过；`python3 tools/project_status.py` 的结构检查通过（报告 80 个可选历史产物链接缺失）。工作树仍包含多个此前任务的用户修改，本轮未清理或回滚这些文件。
