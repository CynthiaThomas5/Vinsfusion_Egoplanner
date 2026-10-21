# EGO 场景导入补丁

- 来源：[DongnanHu6556/ego-planner-ros2-sim 的 ego.sdf](https://github.com/DongnanHu6556/ego-planner-ros2-sim/blob/fdbe8743897b04dd0b8d412f60592d4299b69ef3/ego.sdf)。固定提交 `fdbe8743897b04dd0b8d412f60592d4299b69ef3`。
- 原文件 SHA-256：`92f04e5674bf46fbc7c8fe4fe9cc6b76004305e2877a176c404083fa752250a3`。当前目标及补丁哈希见 [sources.json](../../sources.json) 中 `ego_world`。
- 应用顺序：仅 `0001-ego-harmonic-static-world.patch`；在含固定原版 `ego.sdf` 的下载目录执行 `patch -p1 < <补丁路径>`，产物对应 `simulation/worlds/ego.sdf`。先核对原文件哈希，不能对 main 的后续版本盲目应用。
- 布局规则：将上游 `<state>` 保存的 model pose 物化为静态初始布局，保留 link／visual 局部位姿，移除旧 state 和 Classic GUI；21 个场景模型（地面、四墙模型、19 根圆柱）全部静态化。
- 碰撞修复：16 根圆柱的原 collision 与 visual 半径／高度不一致，按原 visual 修正 collision，防止可见障碍与物理碰撞不一致。原几何和逐项差异见导入报告。
- Harmonic 适配：SDF 1.9、通用 world systems、OGRE2 相机；移除无本地资源的 Classic 材质脚本和默认 shader，保留显式颜色，墙面采用纯色棕色替代砖纹。没有引入无人机、相机、控制器或预制地图。
- 许可：固定仓库文件树及 README 未声明 LICENSE；记录为 `NOT_DECLARED`，仅按用户明确要求导入本地使用，不擅自将该资源改标为本项目或其他依赖的许可。
- 验证报告：[场景导入证据](../../../progress/evidence/ego-world-import-20261021-01.json)。大产物和原版快照位于 `artifacts/runs/ego-world-import-20261021-01/`。
