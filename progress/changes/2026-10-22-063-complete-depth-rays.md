# #063 深度射线完整性

对应[任务摘要](../../collaboration/dialogues/2026-10-22-063-flight-safety-validation.md)。用户本轮已授权持续验证至完整仿真可飞；此处只记录一个已验证修复，不结束整体任务。

EGO patch0038接在0037后：RayCaster使用连续端点的真实方向、正确零轴无穷步长和负向格面交点；深度融合使用map_origin对齐的格坐标、camera→return且不把return格投free票。交叉格／重复端点只去重本帧证据，不截断整条射线；hit和free各最多一次，沿用原有概率更新和>=规则使同帧hit不被重复free稀释。char帧标记在循环使用前清空，避免旧帧别名。没有填未穿越格、没有放宽深度无效或健康门。

新增生产C++回归tools/probe_depth_raycast.cpp，250条确定随机射线逐格对照线段/AABB求交：修复前287错格／287漏格，修复后均0；覆盖轴平行和负向边界，验证共享格不代表后续路径一致。8项目标／几何回归通过；服务器17包构建、183项全回归＋ROS action通过，53文件fresh fetch一致。

两次不解锁冷启动，raw快照free分别10506／14252；这不是严格性能AB，时间和VINS初始化不同。到非free格中心的最大EDT从约0.224到0.447m，仍不是完整0.5m球证书。第二轮启动最早快照为空（首次深度预热未投射），已保存raw-grid-initial；后续明确等待转发>=20帧再采样。实际24次查询包含2个0.05m诊断小球free、1个frame_mismatch；完整机体free未证明。4个状态样本均DISARMED、导航命令0，两会话已关闭。

原始证据与脚本在artifacts/runs/flight-safety-20261022-063-{map-01,map-02,checks}，摘要见[evidence JSON](../evidence/depth-rays-20261022-063.json)。#064继续补全曲线准入与失败终止，尚无本轮飞行通过。
