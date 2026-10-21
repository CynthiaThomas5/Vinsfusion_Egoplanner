# 修改与验证记录

- 任务 ID／日期：#041 / 2026-10-21
- 对话摘要：[任务摘要](../../collaboration/dialogues/2026-10-21-041-ego-route-preview.md)
- 修改文件：新增 artifacts/runs/ego-route-preview-20261021-01 的启动、场景副本、只读样条／快照显示与 RViz 配置；轻量报告及 CURRENT。未修改默认源码、参数和历史产物。
- 行为变化及原因：停掉本轮前序 d435i-preview-20261021-01；新容器 d435i-ego-route-preview-20261021-01 使用 ROS domain 212 和独立 Gazebo partition。复用 #321 第二障碍布局及 #318 实验 planner binary，仅增加 SceneBroadcaster 供 GUI；物理力驱动相机台架，不是无人机飞行。
- 验证类型：静态／planner-only SITL／可视化。启动脚本 bash -n、Python 编译检查；de Boor 插值线性样例和常值端点断言；实际窗口截图检查。初次显示缺 SciPy 后改用 NumPy 实现，Marker topic 配置及视角已修正。
- 结果：本轮实际提交 (2.5,1.4) 平面目标，探针接收两条 B-spline 与对应已接受快照，探针末定位 valid／地图 ready，890 occupied points。RViz 保留本轮首条候选与同 epoch 快照，未向在线地图注入归档数据；显示节点仅发布 /preview 话题及 preview_canvas 的身份坐标变换。
- 证据：[报告](../evidence/ego-route-preview-20261021-01.json)；原始结果、NPZ、日志和截图在 artifacts/runs/ego-route-preview-20261021-01，报告记录哈希。图检查无 truth/control topic 或禁止控制节点。
- 检查：`python3 tools/project_status.py`、`git diff --check` 通过。未重新构建第三方，不把已有实验 overlay 视为默认集成验证。
- 未验证与 PROVISIONAL：路线未执行；当前画面是本轮规划时刻的历史快照与候选，不证明持续定位、完整机体净空、默认配置或飞行验收。阶段状态不变。
- 下一步：按用户查看需求保留窗口；停止仅针对 docker stop d435i-ego-route-preview-20261021-01。后续开发继续 Goal v2，不能把本轮显示计作 S4 或 D 完成。

- 后续用户明确要求关闭：已执行 `docker stop --timeout 10 d435i-ego-route-preview-20261021-01`；关闭本轮容器和窗口，运行产物保留，不清理其他项目。
