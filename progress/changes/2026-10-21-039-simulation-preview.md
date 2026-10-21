# 修改与验证记录

- 任务 ID／日期：#039 / 2026-10-21
- 对话摘要：[任务摘要](../../collaboration/dialogues/2026-10-21-039-simulation-preview.md)
- 修改文件：新增 run-local 启动／会话重启／RViz 配置生成和窗口截图工具，保存在 artifacts/runs/manual-preview-20261021-01；新增轻量证据并更新 CURRENT。
- 行为变化及原因：启动独立容器 d435i-preview-20261021-01，ROS domain 211，独立 Gazebo partition；显示 Gazebo 与 RViz 的在线地图／相机。保留启动失败记录，模型落稳后重启定位／建图为新 epoch。
- 验证类型：脚本静态、六包构建、SITL 未武装可视化。没有控制／飞行验收。
- 命令与结果：bash -n、Python 编译检查通过；当前 src/own 六包 colcon build 通过；窗口截图实际检查通过。新会话状态采样为 TRACKING、地图 ready、1398 occupied points；桥为 DISABLED，armed=false、landed=true，reason=px4_telemetry_stale。结构检查及 git diff --check 通过。
- 结果及证据：[报告](../evidence/manual-preview-20261021-01.json)；构建日志、进程组、截图、PX4／Gazebo／ROS 日志与脚本保存在 artifacts/runs/manual-preview-20261021-01，报告记录主要产物哈希。
- 未验证与 PROVISIONAL：初次初始化超时；重启后观察窗仅能证明短时地图生成。高分辨率 GUI 使 RTF 明显下降，存在 depth_stale 日志和 PX4 telemetry stale，不满足飞行前置门。不升级 S1、P4/P5/P6 或最终条款。
- 下一步：窗口和容器按用户查看需求保持运行；关闭本轮容器使用 docker stop d435i-preview-20261021-01，不清理其他项目进程。后续基线测试恢复固定负载并从新 epoch 开始。
