# GOAL C EGO Fast DDS unread history trace #348

- **任务摘要**：继续调查 EGO camera-pose take 间隔中适配器继续发布、独立 reader 持续收包而 EGO 无 pose take 的现象。
- **用户约束**：保持 P0–P6 范围；旧部署与 ROS_SEARCH 实验只读；保留未提交改动；不得将真值、完整世界地图或控制接口带入最终组合；本轮是诊断，不得把结构或单次仿真当成GOAL C通过。
- **决定**：run-local Fast DDS probe 在每次目标 `rmw_wait` 返回后读取 DataReader unread count，并每16次wait采样matched/lost/rejected；不修改QoS或timeout。
- **结果**：最大1.916 s take间隔中，526次not-ready返回的unread count均为0；唯一ready返回读到25条。publisher与独立reader各观测到40条；33次gap内状态样本matched=1、lost/rejected=0。将现象收窄至EGO DataReader样本交付／进入history路径，底层原因仍未知。wait序号70、71缺失但在选定间隔之外。
- **附带结果**：planner-only样条103个中心线点中41个仍处于当前起点unknown voxel，62个free，曲线未执行。
- **待决问题**：Fast DDS reader未在多数not-ready返回时呈现未读样本的原因是否为传输、reader接收线程、调度或其他reader侧因素？下一轮应使用可区分这些路径的最小实验，同时保持失效关闭策略。
- **证据**：[运行清单](../../artifacts/runs/p2-ego-pose-rmw-unread-history-trace-20261021-348/run-manifest.json)、[报告](../../progress/evidence/p2-ego-pose-rmw-unread-history-trace-20261021-348.json)、[改动记录](../../progress/changes/2026-10-21-015-p2-ego-pose-rmw-unread-history-trace.md)。
