# GOAL C 在线体素快照服务候选 #292

日期：2026-10-20

## 任务摘要

继续推进单 D435i 仿真导航的 GOAL C 地图快照证据。当前 canonical `MapStatus` 不能给出 raw free／unknown 体素；本轮实现并验证一个隔离的只读 `plan_env` 快照服务候选。

## 约束与决定

- 只做 P0–P6 范围内的单 D435i 仿真导航；语义、信念和探索仍只是预留接口。
- `src/vendor` 保持只读，候选 patch 放在 `dependencies/patches/ego`，并记录上游版本、补丁顺序、基线和哈希。
- 快照请求必须精确绑定当前 epoch/map_id，并要求在线融合深度新鲜；raw occupancy 与 inflation mask 分开表示。
- 不启动 controller、PX4 或轨迹执行；不将真值送入定位或建图。
- GOAL C 继续 pending；单次非空快照不能替代覆盖、几何、重影或规划验证。

## 决定与待续

候选 patch 0021 独立于 unknown-as-obstacle 实验 patch 0020，先验证接口传输、身份拒绝和归档回读，不写入 canonical 依赖清单。后续先审查可重建集成方式，再以多场景运动量化覆盖、几何、融合延迟、重影和 unknown-space 行为。

验证命令与运行结果仅保存在对应 `progress/changes`、`progress/evidence` 和 run artifacts，不以本对话摘要作为通过证据。
