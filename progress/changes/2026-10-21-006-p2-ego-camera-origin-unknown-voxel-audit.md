# 修改与验证记录

- 任务 ID／日期：GOAL C EGO 相机射线端点与起点 unknown voxel 源码核对 #331 / 2026-10-21。
- 对话摘要：[2026-10-21-006 对话摘要](../../collaboration/dialogues/2026-10-21-006-p2-ego-camera-origin-unknown-voxel-audit.md)。
- 修改文件：新增 [#331 轻量证据](../evidence/p2-ego-camera-origin-unknown-voxel-source-audit-20261021-331.json)、本记录与对话摘要；更新 GOAL C checklist、CURRENT、证据索引及 EGO patch 说明。仅记录只读源码审计，没有修改自维护或第三方源码。
- 结果：在 #330 目标 MapStatus stamp `22.012 s`，IMU/body位置、由 SDF 外参推导的深度相机中心和 full-spline guard 首拒绝点均投影到地图 voxel `[120,122,1]`。#330 同 epoch 快照确认该格 unknown、inflation=0。固定 EGO 源码从投影表面点向相机位置射线遍历；RayCaster 在相机端点体素返回 false，调用方仅对成功遍历点写 miss/free。新格初始为 unknown，因此射线本身不会清除相机中心格。该机制与 t=0 unknown 观测相符，是强源码支持解释，不是干预因果证明。D435i SDF 的 housing collision box 中心也位于该格，故不能无条件把整格写成普通 free。
- 关键来源：canonical reconstruction upstream `23a8d5a191711dd65633df689bd00f55d4dea8f9`，source tree SHA-256 `09e1ccae79b08279ab55e6fbd1ee550ec4267dda955de51420f1aca392feaad4`。EGO `grid_map.cpp`、`raycast.cpp`、`grid_map.h` 与自维护 adapter、几何 helper、D435i SDF、输入配置的文件 SHA 与行号见 #331 报告。
- 验证：以 #330 保存的精确 odometry stamp 导入 `mapping_input.depth_camera_pose()` 同款 helper 复算；检查地图 `posToIndex`、unknown 初始化、RayCaster endpoint 和 cache update 源码；与 #330 同 epoch snapshot 对齐。未进行新构建或运行，因为源与二进制未更改。
- 限制：这一机制解释当前位姿在 t=0 落入传感器端点所在 unknown cell；不能解释所有非零时间首阻样点，也没有验证安全修复。端点 voxel 与 D435i/机体自身几何重叠，把它直接写成 free 会混淆自机占据与外部未知空间；unknown 仍保持阻塞。
- 下一步：明确 EGO 碰撞查询与机体 footprint/self-filter 的接口契约，并评估 D435i 近场盲区；仅对有几何依据的候选做隔离 planner-only 验证，保留同 epoch 快照和 full-curve 检查。

未提交；保留工作树中已有用户修改，本轮无暂存或提交。
