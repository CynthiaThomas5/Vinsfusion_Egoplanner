# 活跃补丁

只保留`dependencies/sources.json`选中的补丁，顺序、上游commit、应用目录、strip和SHA256以清单为准。

- [VINS](vins/README.md)：9个补丁，固定双目／Jazzy适配、质量遥测、LM、OpenCV线程参数及几何误匹配筛除。
- [EGO](ego/README.md)：17个补丁，地图输入、epoch／目标／取消、仿真时钟、快照、航向起点和停止边界。
- Agent、spdlog：只修改colcon构建元数据。
- 仿真场景：用户指定固定ego.sdf的Harmonic适配，见[来源](simulation/README.md)。

原始GPL／BSD／Apache／MIT许可保持。历史实验补丁已从默认树移出，可恢复审计清单在`dependencies/retired-code-20261021.json`；历史证据不因此改判。源重建、构建和SITL分别验证。

## 非默认硬件诊断候选

[PX4同步边界计时](px4/README.md)为HW10-SYNC-018的隔离构建候选，不在`dependencies/sources.json`默认补丁列表，不参与冻结仿真/生产构建，也未部署实机。其基准、应用顺序、许可和验证单独记录；不能把构建通过当成实机资格。
