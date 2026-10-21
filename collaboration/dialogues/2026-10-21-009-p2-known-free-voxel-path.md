# 重新观测后 guard 目标的 known-free 路径复核

用户要求继续完成项目 `GOAL.md`。本轮沿 GOAL C 的 #332→#337 证据链，检查 pitch 后同一地图中 guard 目标是否与 VINS 当前起点之间存在只经过 known-free、未膨胀体素的路径。

约束与决定：读取 #337 同 epoch、同 `map_id` 的快照；使用 D435i SDF 外参反算定位器 IMU 起点；unknown、occupied、inflated 一律阻塞，仅允许当前起点所在的单个 voxel 作为已存在的状态，不运行 ROS/Gazebo/PX4，不发目标、不读真值、不发布控制。该分析不能作为 EGO 样条、机体净空或 GOAL C 通过证据。

结果：baseline 起点格 `[119,119,1]` 与 guard 目标格 `[122,118,5]` 均 unknown，起点格豁免后没有 known-free 连通区域。pitch 后起点 `[120,119,1]` 仍 unknown，但目标格变为 free 且 inflation=0；存在 8 格、7 条边（0.7 m 栅格边长）的 6 邻接路径，起点之后的每一格均 known-free 且 inflation=0。独立回读确认同一 epoch/map_id 与所有路径格属性。

下一步：用独立 ROS domain 对 pitch 后地图运行 planner-only 目标请求，并对实际样条做同 stamp voxel 快照校验；保留 unknown fail-closed 和唯一起点格例外。若 EGO 起点守卫拒绝，先审查起点／传感器自体 footprint 合同，不全局清未知。PX4 SITL 的视角动作与机体扫掠净空另行验证。
