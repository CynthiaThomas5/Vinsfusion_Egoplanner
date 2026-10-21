# EGO 快照服务依赖重建

- 用户约束：继续完成 GOAL A–H；不修改第三方来源，不把结构或构建通过夸大为地图、规划或飞行验收；只推进单 D435i 仿真。
- 目标：将已验证的 EGO occupancy snapshot patch 0021 放进固定、可重建的依赖链，并在不修改 `src/vendor` 的条件下复建和构建。
- 决定：patch 0021 排在 canonical patch 0019 后；unknown-as-obstacle patch 0020 继续隔离。取源流程根据 patch 实际路径记录工作目录和 strip 层数，克隆 pinned upstream 后只导入五个 planner 包。
- 结果：工具离线安全测试通过；真实上游 commit `23a8d5a191711dd65633df689bd00f55d4dea8f9` 与许可证哈希校验通过，15补丁重建成功；新 build/install 中16个 colcon 包全部通过，快照 service interface 可查询。现有 `src/vendor/ego_planner` 保持不变。
- 边界：这是依赖重建、编译和接口存在性证据。#292–#296 的地图内容仍稀疏，墙面一格变化与部分 SDF 离群点未解释；GOAL C、规划、控制及最终视觉验收仍 pending。
- 下一步：继续 matched-phase 可见 ROI 的覆盖、栅格量化与离群点诊断，再推进正式地图指标和 P4/P5/P6 缺口。
