# #603 RViz 第一视角试验与撤回

- 用户要求试验 D435i 相机第一视角，并观察 EGO 柱群 16m 路线。试验版加入 RViz Camera display 和仿真用相机 TF；实际 GUI 中曾验证第一视角图像及地图视图。
- 柱群 16m 任务 `gui-20261030-162149-3867210`：`qualification.json` PASS；独立到达判据 PASS；禁入碰撞数 0；正常落地上锁；safe-to-stop PASS。最小离线真值位置误差 0.04185m，连续联合容差窗口 5.78s。
- 验证命令：试验版 `colcon build --base-paths src/own --packages-up-to uav_localization` PASS（3 packages）；`./start.sh fly pillars` PASS；运行时 RViz 订阅 RGB、CameraInfo、地图和路径，试验 TF 约 148Hz。
- 用户随后要求恢复最开始视图并停止继续。故第一视角 Camera、TF 代码和持久化浮动布局已撤回；这份报告只记录已发生的试验和仿真，不代表保留的第一视角功能或项目里程碑通过。
- 飞行与可视化试验产物位于 `artifacts/runs/gui-20261030-162149-3867210/`；第一视角试验截图为 `rviz-fpv-main.png`，任务结果为 `qualification.json`、`arrival-evaluation.json`、`vehicle-contact-evaluation.json`。
